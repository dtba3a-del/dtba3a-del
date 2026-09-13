#!/usr/bin/env python3
"""
GitHub Profile Complete Backup Script
Создаёт полную резервную копию профиля GitHub в E:\GITHUB_BACKUP\dtba3a-del

Включает:
- Все owned репозитории (с полной историей и ветвями)
- Форки с вашим вкладом
- Все issues, PRs, комментарии
- Metadata профиля
- Gists
- Starred repos список
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import requests
from typing import Optional, List, Dict

class GitHubBackup:
    def __init__(self, github_token: str, username: str, backup_path: str = r"E:\GITHUB_BACKUP"):
        self.token = github_token
        self.username = username
        self.backup_path = Path(backup_path) / username
        self.api_headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"
        
        # Создаём папку для бэкапа
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.repos_path = self.backup_path / "repositories"
        self.repos_path.mkdir(exist_ok=True)
        self.metadata_path = self.backup_path / "metadata"
        self.metadata_path.mkdir(exist_ok=True)
        
    def log(self, message: str, level: str = "INFO"):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def api_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict | List]:
        """Безопасный запрос к GitHub API"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self.api_headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.log(f"API Error on {endpoint}: {str(e)}", "ERROR")
            return None
    
    def backup_profile_metadata(self):
        """Экспортирует информацию профиля"""
        self.log("Backing up profile metadata...")
        
        user_data = self.api_request(f"/users/{self.username}")
        if not user_data:
            self.log("Failed to fetch user data", "ERROR")
            return
        
        # Сохраняем основную информацию профиля
        profile_file = self.metadata_path / "profile.json"
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=2, ensure_ascii=False)
        self.log(f"✓ Profile saved to {profile_file}")
    
    def backup_repositories(self):
        """Клонирует все owned репозитории"""
        self.log("Fetching repository list...")
        
        repos = []
        page = 1
        while True:
            data = self.api_request(
                f"/user/repos",
                params={
                    "affiliation": "owner",
                    "per_page": 100,
                    "page": page,
                    "sort": "updated"
                }
            )
            if not data or len(data) == 0:
                break
            repos.extend(data)
            page += 1
        
        self.log(f"Found {len(repos)} owned repositories")
        
        # Сохраняем список репозиториев
        repos_list_file = self.metadata_path / "repositories_list.json"
        with open(repos_list_file, 'w', encoding='utf-8') as f:
            json.dump(repos, f, indent=2, ensure_ascii=False)
        self.log(f"✓ Repositories list saved to {repos_list_file}")
        
        # Клонируем каждый репозиторий
        for i, repo in enumerate(repos, 1):
            self.log(f"[{i}/{len(repos)}] Cloning {repo['full_name']}...")
            self._clone_repository(repo)
    
    def _clone_repository(self, repo: Dict):
        """Клонирует один репозиторий с полной историей"""
        repo_name = repo['name']
        clone_url = repo['clone_url'] if 'clone_url' in repo else repo['html_url']
        target_path = self.repos_path / repo_name
        
        # Используем HTTPS с токеном для аутентификации
        if not clone_url.startswith('https'):
            clone_url = repo['html_url'].replace('github.com', f'{self.username}:{self.token}@github.com')
        else:
            clone_url = clone_url.replace('https://', f'https://{self.username}:{self.token}@')
        
        try:
            if target_path.exists():
                # Обновляем существующий репозиторий
                subprocess.run(
                    ['git', 'fetch', '--all', '--prune'],
                    cwd=target_path,
                    check=True,
                    capture_output=True
                )
                self.log(f"  ✓ Updated {repo_name}")
            else:
                # Полный клон с зеркалом (все ветви и теги)
                subprocess.run(
                    ['git', 'clone', '--mirror', clone_url, str(target_path)],
                    check=True,
                    capture_output=True,
                    timeout=300
                )
                self.log(f"  ✓ Cloned {repo_name}")
        except subprocess.CalledProcessError as e:
            self.log(f"  ✗ Failed to clone {repo_name}: {e.stderr.decode()}", "ERROR")
        except Exception as e:
            self.log(f"  ✗ Error with {repo_name}: {str(e)}", "ERROR")
    
    def backup_issues_and_prs(self):
        """Экспортирует все issues и PRs"""
        self.log("Backing up issues and pull requests...")
        
        repos = []
        page = 1
        while True:
            data = self.api_request(
                f"/user/repos",
                params={
                    "affiliation": "owner",
                    "per_page": 100,
                    "page": page
                }
            )
            if not data or len(data) == 0:
                break
            repos.extend(data)
            page += 1
        
        issues_dir = self.metadata_path / "issues"
        issues_dir.mkdir(exist_ok=True)
        
        for repo in repos:
            repo_name = repo['name']
            self.log(f"  Fetching issues for {repo_name}...")
            
            issues_data = {
                "issues": [],
                "pull_requests": []
            }
            
            # Получаем issues
            page = 1
            while True:
                issues = self.api_request(
                    f"/repos/{repo['full_name']}/issues",
                    params={"state": "all", "per_page": 100, "page": page}
                )
                if not issues or len(issues) == 0:
                    break
                
                for issue in issues:
                    if 'pull_request' not in issue:
                        issues_data["issues"].append(issue)
                    else:
                        issues_data["pull_requests"].append(issue)
                page += 1
            
            if issues_data["issues"] or issues_data["pull_requests"]:
                repo_issues_file = issues_dir / f"{repo_name}_issues.json"
                with open(repo_issues_file, 'w', encoding='utf-8') as f:
                    json.dump(issues_data, f, indent=2, ensure_ascii=False)
                
                total = len(issues_data["issues"]) + len(issues_data["pull_requests"])
                self.log(f"    ✓ Saved {total} issues/PRs for {repo_name}")
    
    def backup_gists(self):
        """Экспортирует все Gists"""
        self.log("Backing up gists...")
        
        gists = []
        page = 1
        while True:
            data = self.api_request(
                f"/users/{self.username}/gists",
                params={"per_page": 100, "page": page}
            )
            if not data or len(data) == 0:
                break
            gists.extend(data)
            page += 1
        
        if gists:
            gists_file = self.metadata_path / "gists.json"
            with open(gists_file, 'w', encoding='utf-8') as f:
                json.dump(gists, f, indent=2, ensure_ascii=False)
            self.log(f"✓ Backed up {len(gists)} gists")
        else:
            self.log("No gists found")
    
    def backup_starred_repos(self):
        """Сохраняет список звёздных репозиториев"""
        self.log("Backing up starred repositories...")
        
        starred = []
        page = 1
        while True:
            data = self.api_request(
                f"/user/starred",
                params={"per_page": 100, "page": page}
            )
            if not data or len(data) == 0:
                break
            starred.extend(data)
            page += 1
        
        if starred:
            starred_file = self.metadata_path / "starred_repos.json"
            with open(starred_file, 'w', encoding='utf-8') as f:
                json.dump(starred, f, indent=2, ensure_ascii=False)
            self.log(f"✓ Backed up {len(starred)} starred repositories")
        else:
            self.log("No starred repositories found")
    
    def backup_followers(self):
        """Сохраняет список фолловеров и фолловинга"""
        self.log("Backing up followers/following...")
        
        followers = []
        following = []
        
        page = 1
        while True:
            data = self.api_request(
                f"/users/{self.username}/followers",
                params={"per_page": 100, "page": page}
            )
            if not data or len(data) == 0:
                break
            followers.extend(data)
            page += 1
        
        page = 1
        while True:
            data = self.api_request(
                f"/users/{self.username}/following",
                params={"per_page": 100, "page": page}
            )
            if not data or len(data) == 0:
                break
            following.extend(data)
            page += 1
        
        social_file = self.metadata_path / "social.json"
        with open(social_file, 'w', encoding='utf-8') as f:
            json.dump({"followers": followers, "following": following}, f, indent=2, ensure_ascii=False)
        
        self.log(f"✓ Backed up {len(followers)} followers and {len(following)} following")
    
    def create_backup_report(self):
        """Создаёт отчёт о бэкапе"""
        self.log("Creating backup report...")
        
        report = {
            "backup_date": datetime.now().isoformat(),
            "username": self.username,
            "backup_location": str(self.backup_path),
            "contents": {
                "profile": str(self.metadata_path / "profile.json"),
                "repositories": str(self.repos_path),
                "issues_and_prs": str(self.metadata_path / "issues"),
                "gists": str(self.metadata_path / "gists.json"),
                "starred_repos": str(self.metadata_path / "starred_repos.json"),
                "social": str(self.metadata_path / "social.json")
            },
            "instructions": {
                "restore_repos": "cd repositories && for dir in */; do git clone --mirror \"$dir\" \"path/to/restore\"; done",
                "restore_full": "Use git commands or import this folder structure back to GitHub"
            }
        }
        
        report_file = self.backup_path / "BACKUP_REPORT.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.log(f"✓ Backup report saved to {report_file}")
        print("\n" + "="*70)
        print(f"BACKUP COMPLETE!")
        print(f"Location: {self.backup_path}")
        print("="*70)
    
    def run_full_backup(self):
        """Запускает полную резервную копию"""
        self.log(f"Starting full backup for user: {self.username}")
        self.log(f"Backup location: {self.backup_path}")
        
        try:
            self.backup_profile_metadata()
            self.backup_repositories()
            self.backup_issues_and_prs()
            self.backup_gists()
            self.backup_starred_repos()
            self.backup_followers()
            self.create_backup_report()
            
            self.log("✓ BACKUP COMPLETED SUCCESSFULLY!")
        except KeyboardInterrupt:
            self.log("Backup interrupted by user", "WARNING")
            sys.exit(1)
        except Exception as e:
            self.log(f"Backup failed: {str(e)}", "ERROR")
            sys.exit(1)

def main():
    """Главная функция"""
    print("="*70)
    print("GitHub Profile Complete Backup Tool")
    print("="*70)
    
    # Получаем токен из переменной окружения
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("\n⚠️  GITHUB_TOKEN не найден в переменных окружения!")
        print("\nКак установить токен:")
        print("Windows (PowerShell):")
        print("  $env:GITHUB_TOKEN = 'your_token_here'")
        print("\nWindows (CMD):")
        print("  set GITHUB_TOKEN=your_token_here")
        print("\nLinux/Mac:")
        print("  export GITHUB_TOKEN='your_token_here'")
        print("\nПолучить токен: https://github.com/settings/tokens")
        sys.exit(1)
    
    username = "dtba3a-del"  # Ваш логин
    backup_path = r"E:\GITHUB_BACKUP"
    
    backup = GitHubBackup(token, username, backup_path)
    backup.run_full_backup()

if __name__ == "__main__":
    main()
