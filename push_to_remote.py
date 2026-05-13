# -*- coding: utf-8 -*-
"""
代码推送脚本 - 使用 git 命令将代码推送到 GitHub 和 Gitee
用法: python push_to_remote.py [--github] [--gitee] [--dry-run]
  默认推送到两个平台，可指定只推一个
  --dry-run 只显示将要推送的文件，不实际执行
"""
import os
import sys
import subprocess
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from push_config import COMMIT_MESSAGE, FILES, GITHUB, GITEE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_git(*args, check=True):
    result = subprocess.run(
        ["git"] + list(args),
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        print(f"  GIT ERROR: {result.stderr.strip()}")
        return None
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Push code to GitHub and Gitee")
    parser.add_argument("--github", action="store_true", help="Only push to GitHub")
    parser.add_argument("--gitee", action="store_true", help="Only push to Gitee")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be pushed")
    args = parser.parse_args()

    do_github = args.github or (not args.github and not args.gitee)
    do_gitee = args.gitee or (not args.github and not args.gitee)

    print("=" * 60)
    print("文件清单：")
    for rel_path in FILES:
        abs_path = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))
        status = "OK" if os.path.exists(abs_path) else "MISSING"
        print(f"  [{status}] {rel_path}")
    print()

    if args.dry_run:
        print("[DRY-RUN] 以下文件将被添加、提交并推送：")
        for rel_path in FILES:
            print(f"  + {rel_path}")
        print(f"\nCommit message:\n{COMMIT_MESSAGE}")
        if do_github:
            print(f"\n将推送到 GitHub: {GITHUB['owner']}/{GITHUB['repo']}@{GITHUB['branch']}")
        if do_gitee:
            print(f"将推送到 Gitee:  {GITEE['owner']}/{GITEE['repo']}@{GITEE['branch']}")
        return

    print("Step 1: git add ...")
    for rel_path in FILES:
        abs_path = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))
        if os.path.exists(abs_path):
            run_git("add", abs_path)
            print(f"  added: {rel_path}")

    print("\nStep 2: git commit ...")
    msg_file = os.path.join(BASE_DIR, "_commit_msg.tmp")
    with open(msg_file, "w", encoding="utf-8") as f:
        f.write(COMMIT_MESSAGE)
    result = run_git("commit", "-F", msg_file, check=False)
    if os.path.exists(msg_file):
        os.remove(msg_file)
    if result is not None:
        print(f"  {result.split(chr(10))[0] if result else 'committed'}")
    else:
        print("  (nothing to commit or commit failed)")

    local_branch = run_git("rev-parse", "--abbrev-ref", "HEAD") or "master"

    if do_gitee:
        print(f"\nStep 3a: git push origin {local_branch}:{GITEE['branch']} (Gitee) ...")
        result = run_git("push", "origin", f"{local_branch}:{GITEE['branch']}", check=False)
        if result is not None:
            print(f"  Gitee push done.")
        else:
            print("  Gitee push may have failed, check above.")

    if do_github:
        print(f"\nStep 3b: git push github {local_branch}:{GITHUB['branch']} (GitHub) ...")
        result = run_git("push", "github", f"{local_branch}:{GITHUB['branch']}", check=False)
        if result is not None:
            print(f"  GitHub push done.")
        else:
            print("  GitHub push may have failed, check above.")

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
