#!/usr/bin/env python3
"""
GitHub Profile Complete Backup Script
Полная резервная копия профиля GitHub в E:\GITHUB_BACKUP\dtba3a-del

Использует уже авторизованный gh CLI
Клонирует все owned репозитории с полной историей и ветвями
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

class GitHubBackup:
    def __init__(self, username: str, backup_path: str = r"E:\GITHUB_BACKUP"):
        self.username = username
        self.backup_path = Path(backup_path) / username
        
        # Создаём структуру папок
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.repos_path = self.backup_path / "repositories"
        self.repos_path.mkdir(exist_ok=True)
        self.metadata_path = self.backup_path / "metadata"
        self.metadata_path.mkdir(exist_ok=True)
        
        # Проверяем gh CLI
        self._check_gh_auth()
    
    def _check_gh_auth(self):
        """Проверяет авторизацию gh"""
        try:
            result = subprocess.run(
                ['gh', 'auth', 'status'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                self.log("gh CLI не авторизован!", "ERROR")
                self.log("Выполните: gh auth login", "ERROR")
                sys.exit(1)
            self.log("✓ gh CLI авторизован")
        except FileNotFoundError:
            self.log("gh CLI не установлен!", "ERROR")
            self.log("Скачайте с https://cli.github.com", "ERROR")
            sys.exit(1)
    
    def log(self, message: str, level: str = "INFO"):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def gh_api(self, endpoint: str, raw: bool = False) -> Optional[Dict | List | str]:
        """Запрос через gh API"""
        try:
            cmd = ['gh', 'api']
            if raw:
                cmd.append('--raw')
            cmd.append(endpoint)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.log(f"API Error on {endpoint}: {result.stderr}", "ERROR")
                return None
            
            if raw:
                return result.stdout
            return json.loads(result.stdout)
        except Exception as e:
            self.log(f"API Error on {endpoint}: {str(e)}", "ERROR")
            return None
    
    def backup_profile_metadata(self):
        """Экспортирует информацию профиля"""
        self.log("Backing up profile metadata...")
        
        user_data = self.gh_api(f"/users/{self.username}")
        if not user_data:
            self.log("Failed to fetch user data", "ERROR")
            return
        
        profile_file = self.metadata_path / "profile.json"
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=2, ensure_ascii=False)
        self.log(f"✓ Profile saved to {profile_file}")
    
    def backup_repositories(self):
        """Клонирует все owned репозитории"""
        self.log("Fetching repository list...")
        
        # Используем gh для получения списка репо
        try:
            result = subprocess.run(
                ['gh', 'repo', 'list', self.username, '--limit', '1000', '--json', 'name,url,defaultBranchRef'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                self.log(f"Failed to fetch repos: {result.stderr}", "ERROR")
                return
            
            repos = json.loads(result.stdout)
        except Exception as e:
            self.log(f"Error fetching repos: {str(e)}", "ERROR")
            return
        
        self.log(f"Found {len(repos)} repositories")
        
        # Сохраняем список репозиториев
        repos_list_file = self.metadata_path / "repositories_list.json"
        with open(repos_list_file, 'w', encoding='utf-8') as f:
            json.dump(repos, f, indent=2, ensure_ascii=False)
        self.log(f"✓ Repositories list saved")
        
        # Клонируем каждый репозиторий
        for i, repo in enumerate(repos, 1):
            self.log(f"[{i}/{len(repos)}] Cloning {repo['name']}...")
            self._clone_repository(repo)
    
    def _clone_repository(self, repo: Dict):
        """Клонирует один репозиторий с полной историей"""
        repo_name = repo['name']
        clone_url = repo['url']
        target_path = self.repos_path / repo_name
        
        try:
            if target_path.exists():
                # Обновляем существующий репозиторий
                subprocess.run(
                    ['git', 'fetch', '--all', '--prune', '--tags'],
                    cwd=target_path,
                    check=True,
                    capture_output=True,
                    timeout=300
                )
                self.log(f"  ✓ Updated {repo_name}")
            else:
                # Полный клон с зеркалом (все ветви и теги)
                subprocess.run(
                    ['git', 'clone', '--mirror', clone_url, str(target_path)],
                    check=True,
                    capture_output=True,
                    timeout=600
                )
                self.log(f"  ✓ Cloned {repo_name}")
        except subprocess.CalledProcessError as e:
            self.log(f"  ✗ Failed to clone {repo_name}: {e.stderr.decode() if e.stderr else str(e)}", "ERROR")
        except subprocess.TimeoutExpired:
            self.log(f"  ✗ Timeout cloning {repo_name}", "ERROR")
        except Exception as e:
            self.log(f"  ✗ Error with {repo_name}: {str(e)}", "ERROR")
    
    def backup_issues_and_prs(self):
        """Экспортирует все issues и PRs"""
        self.log("Backing up issues and pull requests...")
        
        try:
            result = subprocess.run(
                ['gh', 'repo', 'list', self.username, '--limit', '1000', '--json', 'name,nameWithOwner'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return
            
            repos = json.loads(result.stdout)
        except Exception as e:
            self.log(f"Error fetching repos for issues: {str(e)}", "ERROR")
            return
        
        issues_dir = self.metadata_path / "issues"
        issues_dir.mkdir(exist_ok=True)
        
        for repo in repos:
            repo_name = repo['name']
            repo_full = repo['nameWithOwner']
            
            try:
                # Получаем issues
                result = subprocess.run(
                    ['gh', 'issue', 'list', '-R', repo_full, '--limit', '1000', '--json', 
                     'number,title,state,body,createdAt,updatedAt,comments,author'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    continue
                
                issues = json.loads(result.stdout)
                
                # Получаем PRs
                result = subprocess.run(
                    ['gh', 'pr', 'list', '-R', repo_full, '--limit', '1000', '--json',
                     'number,title,state,body,createdAt,updatedAt,comments,author'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                prs = json.loads(result.stdout) if result.returncode == 0 else []
                
                if issues or prs:
                    data = {"issues": issues, "pull_requests": prs}
                    repo_issues_file = issues_dir / f"{repo_name}_issues.json"
                    with open(repo_issues_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    total = len(issues) + len(prs)
                    self.log(f"  ✓ Saved {total} issues/PRs for {repo_name}")
            
            except Exception as e:
                self.log(f"  Error processing {repo_name}: {str(e)}", "WARNING")
    
    def backup_gists(self):
        """Экспортирует все Gists"""
        self.log("Backing up gists...")
        
        try:
            result = subprocess.run(
                ['gh', 'gist', 'list', '--limit', '1000', '--json', 'name,description,files,createdAt,updatedAt'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                self.log("No gists found or error fetching", "WARNING")
                return
            
            gists = json.loads(result.stdout)
            
            if gists:
                gists_file = self.metadata_path / "gists.json"
                with open(gists_file, 'w', encoding='utf-8') as f:
                    json.dump(gists, f, indent=2, ensure_ascii=False)
                self.log(f"✓ Backed up {len(gists)} gists")
            else:
                self.log("No gists found")
        except Exception as e:
            self.log(f"Error backing up gists: {str(e)}", "WARNING")
    
    def backup_starred_repos(self):
        """Сохраняет список звёздных репозиториев"""
        self.log("Backing up starred repositories...")
        
        try:
            result = subprocess.run(
                ['gh', 'api', f'users/{self.username}/starred', '--paginate', '--jq', '.[]'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                self.log("Error fetching starred repos", "WARNING")
                return
            
            # Парсим JSON объекты из вывода
            starred = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        starred.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            
            if starred:
                starred_file = self.metadata_path / "starred_repos.json"
                with open(starred_file, 'w', encoding='utf-8') as f:
                    json.dump(starred, f, indent=2, ensure_ascii=False)
                self.log(f"✓ Backed up {len(starred)} starred repositories")
            else:
                self.log("No starred repositories found")
        except Exception as e:
            self.log(f"Error backing up starred repos: {str(e)}", "WARNING")
    
    def backup_followers(self):
        """Сохраняет список фолловеров и фолловинга"""
        self.log("Backing up followers/following...")
        
        try:
            # Followers
            result = subprocess.run(
                ['gh', 'api', f'users/{self.username}/followers', '--paginate', '--jq', '.[]'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            followers = []
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            followers.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            
            # Following
            result = subprocess.run(
                ['gh', 'api', f'users/{self.username}/following', '--paginate', '--jq', '.[]'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            following = []
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            following.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            
            social_file = self.metadata_path / "social.json"
            with open(social_file, 'w', encoding='utf-8') as f:
                json.dump({"followers": followers, "following": following}, f, indent=2, ensure_ascii=False)
            
            self.log(f"✓ Backed up {len(followers)} followers and {len(following)} following")
        except Exception as e:
            self.log(f"Error backing up social data: {str(e)}", "WARNING")
    
    def create_backup_report(self):
        """Создаёт отчёт о бэкапе"""
        self.log("Creating backup report...")
        
        report = {
            "backup_date": datetime.now().isoformat(),
            "username": self.username,
            "backup_location": str(self.backup_path),
            "contents": {
                "profile": "metadata/profile.json",
                "repositories": "repositories/",
                "issues_and_prs": "metadata/issues/",
                "gists": "metadata/gists.json",
                "starred_repos": "metadata/starred_repos.json",
                "social": "metadata/social.json"
            },
            "notes": {
                "repositories": "Хранятся как git bare repositories (.git)",
                "restore": "Используйте 'git clone <path>' для восстановления",
                "metadata": "Все метаданные в JSON для портативности"
            }
        }
        
        report_file = self.backup_path / "BACKUP_REPORT.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.log(f"✓ Backup report saved to {report_file}")
        print("\n" + "="*70)
        print(f"✓ BACKUP COMPLETE!")
        print(f"Location: {self.backup_path}")
        print("="*70)
    
    def run_full_backup(self):
        """Запускает полную резервную копию"""
        self.log(f"Starting full backup for user: {self.username}")
        self.log(f"Backup location: {self.backup_path}")
        print()
        
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
    print("Использует gh CLI (авторизация уже готова)")
    print("="*70)
    print()
    
    username = "dtba3a-del"
    backup_path = r"E:\GITHUB_BACKUP"
    
    backup = GitHubBackup(username, backup_path)
    backup.run_full_backup()

if __name__ == "__main__":
    main()
