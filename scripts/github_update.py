#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 更新命令行工具
使用示例:
    python github_update.py --status          # 检查状态
    python github_update.py --update           # 更新代码
    python github_update.py --update --branch main  # 更新到main分支
    python github_update.py --history --limit 20     # 查看提交历史
"""

import sys
import os
import argparse
import json
from tools.github.github_updater import GitHubUpdater


def print_status(status):
    """打印状态信息"""
    print("=" * 50)
    print("Git 仓库状态")
    print("=" * 50)
    
    if not status['is_git_repo']:
        print(f"❌ {status.get('error', '不是 Git 仓库')}")
        return
    
    print(f"✅ Git 仓库: {status['is_git_repo']}")
    print(f"📍 当前分支: {status.get('current_branch', 'Unknown')}")
    print(f"🔗 远程仓库: {status.get('remote_url', 'Unknown')}")
    print(f"📝 最新提交: {status.get('last_commit', 'Unknown')[:50]}...")
    
    if status['has_changes']:
        print("⚠️  存在未提交的更改")
    else:
        print("✅ 工作目录干净")
    
    if status['behind_commits'] > 0:
        print(f"📥 落后远程 {status['behind_commits']} 个提交")
    elif status['ahead_commits'] > 0:
        print(f"📤 领先远程 {status['ahead_commits']} 个提交")
    else:
        print("✅ 与远程同步")


def print_update_result(result):
    """打印更新结果"""
    print("\n" + "=" * 50)
    print("更新结果")
    print("=" * 50)
    
    if result['success']:
        print(f"✅ {result['message']}")
        
        if result.get('backup_created'):
            print(f"💾 备份位置: {result['backup_path']}")
        
        if result.get('updated_files'):
            print(f"\n📁 更新的文件 ({len(result['updated_files'])} 个):")
            for file in result['updated_files'][:10]:  # 只显示前10个
                print(f"  - {file}")
            if len(result['updated_files']) > 10:
                print(f"  ... 还有 {len(result['updated_files']) - 10} 个文件")
    else:
        print(f"❌ 更新失败: {result.get('error', '未知错误')}")


def print_commits(commits):
    """打印提交历史"""
    print("\n" + "=" * 50)
    print("提交历史")
    print("=" * 50)
    
    if not commits:
        print("没有找到提交记录")
        return
    
    for i, commit in enumerate(commits, 1):
        print(f"{i:2d}. {commit['hash'][:8]} - {commit['message'][:60]}")
        print(f"     👤 {commit['author']}  📅 {commit['date'][:19]}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='GitHub 更新工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --status                    检查 Git 状态
  %(prog)s --update                    更新到最新版本
  %(prog)s --update --branch main      更新到 main 分支
  %(prog)s --update --no-backup        更新但不创建备份
  %(prog)s --history                   查看提交历史
  %(prog)s --history --limit 20        查看最近20个提交
  %(prog)s --rollback abc123           回滚到指定提交
        """
    )
    
    # 路径参数
    parser.add_argument('--path', '-p', help='仓库路径 (默认: 当前目录)')
    
    # 操作参数
    parser.add_argument('--status', '-s', action='store_true', help='检查 Git 仓库状态')
    parser.add_argument('--update', '-u', action='store_true', help='从 GitHub 更新代码')
    parser.add_argument('--history', '-n', action='store_true', help='查看提交历史')
    parser.add_argument('--rollback', '-r', help='回滚到指定提交')
    parser.add_argument('--branches', '-b', action='store_true', help='查看所有分支')
    
    # 更新选项
    parser.add_argument('--branch', help='目标分支 (默认: 当前分支)')
    parser.add_argument('--no-backup', action='store_true', help='更新时不创建备份')
    parser.add_argument('--limit', type=int, default=10, help='历史记录数量 (默认: 10)')
    
    # 输出选项
    parser.add_argument('--json', action='store_true', help='以 JSON 格式输出')
    
    args = parser.parse_args()
    
    # 如果没有指定任何操作，显示帮助
    if not any([args.status, args.update, args.history, args.rollback, args.branches]):
        parser.print_help()
        return
    
    try:
        updater = GitHubUpdater(args.path)
        
        if args.status:
            status = updater.check_git_status()
            if args.json:
                print(json.dumps(status, indent=2, ensure_ascii=False))
            else:
                print_status(status)
        
        elif args.update:
            print("开始从 GitHub 更新代码...")
            result = updater.update_from_github(
                branch=args.branch,
                backup=not args.no_backup
            )
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print_update_result(result)
        
        elif args.history:
            commits = updater.get_commit_history(args.limit)
            if args.json:
                print(json.dumps(commits, indent=2, ensure_ascii=False))
            else:
                print_commits(commits)
        
        elif args.rollback:
            print(f"警告: 即将回滚到提交 {args.rollback[:8]}")
            confirm = input("确认继续? (y/N): ").strip().lower()
            if confirm == 'y':
                result = updater.rollback_to_commit(args.rollback)
                if args.json:
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                else:
                    if result['success']:
                        print(f"✅ {result['message']}")
                    else:
                        print(f"❌ {result.get('error', '回滚失败')}")
            else:
                print("操作已取消")
        
        elif args.branches:
            success, local_branches, _ = updater._run_git_command(['branch', '--format=%(refname:short)'])
            success, remote_branches, _ = updater._run_git_command(['branch', '-r', '--format=%(refname:short)'])
            
            if args.json:
                result = {
                    "local": [b.strip() for b in local_branches.split('\n') if b.strip()],
                    "remote": [b.strip() for b in remote_branches.split('\n') if b.strip()]
                }
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print("\n" + "=" * 50)
                print("分支列表")
                print("=" * 50)
                print("📍 本地分支:")
                for branch in local_branches.split('\n'):
                    if branch.strip():
                        print(f"  - {branch.strip()}")
                
                print("\n🌐 远程分支:")
                for branch in remote_branches.split('\n'):
                    if branch.strip():
                        print(f"  - {branch.strip()}")
    
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()