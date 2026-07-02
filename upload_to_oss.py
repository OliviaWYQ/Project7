#!/usr/bin/env python3
"""上传 libero 数据集到阿里云 OSS

用法:
  python3 upload_to_oss.py
"""

import os
import sys
import time
import oss2
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ── 配置（可按需修改） ──────────────────────────────────
ENDPOINT = "oss-cn-shenzhen.aliyuncs.com"
BUCKET_NAME = "gr00t"
OSS_PREFIX = "libero_object_no_noops_lerobot/"
# 本地数据路径（相对于脚本所在目录）
LOCAL_DIR = Path(__file__).resolve().parent / "libero_object_no_noops_lerobot"
MAX_WORKERS = 8
MAX_RETRIES = 3

# 凭证：环境变量优先
ACCESS_KEY_ID = os.environ.get("OSS_AK")
ACCESS_KEY_SECRET = os.environ.get("OSS_SK")

lock = threading.Lock()
completed = 0
failed = 0
total = 0
skipped = 0
uploaded_bytes = 0

def upload_file(bucket, local_path, oss_key, size):
    global completed, failed, skipped, uploaded_bytes
    
    for attempt in range(MAX_RETRIES):
        try:
            bucket.put_object_from_file(oss_key, str(local_path))
            with lock:
                completed += 1
                uploaded_bytes += size
                if (completed + skipped) % 50 == 0 or completed <= 5:
                    mb = uploaded_bytes / (1024 * 1024)
                    print(f"  [进度] 完成 {completed}，失败 {failed} / {total} | {mb:.1f}MB", flush=True)
            return True, oss_key
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                with lock:
                    failed += 1
                    print(f"  [失败] {oss_key}: {e}", flush=True)
                return False, oss_key

def main():
    global total, skipped, completed, failed, uploaded_bytes
    
    print("=" * 65)
    print(f"上传到 OSS: oss://{BUCKET_NAME}/{OSS_PREFIX}")
    print(f"Endpoint: {ENDPOINT}")
    print(f"源目录: {LOCAL_DIR}")
    print("=" * 65)
    
    # 初始化 OSS client
    auth = oss2.Auth(ACCESS_KEY_ID, ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, ENDPOINT, BUCKET_NAME)
    
    # 测试连接
    try:
        bucket.get_bucket_info()
        print("\n✓ OSS 连接成功\n")
    except Exception as e:
        print(f"\n✗ OSS 连接失败: {e}")
        sys.exit(1)
    
    # 收集所有文件
    tasks = []
    for root, dirs, files in os.walk(LOCAL_DIR):
        for fname in files:
            local_path = Path(root) / fname
            rel_path = local_path.relative_to(LOCAL_DIR)
            oss_key = OSS_PREFIX.rstrip('/') + '/' + str(rel_path)
            size = local_path.stat().st_size
            tasks.append((local_path, oss_key, size))
    
    total = len(tasks)
    total_size = sum(t[2] for t in tasks)
    print(f"共 {total} 个文件，总计 {total_size/(1024*1024):.1f} MB\n")
    
    # 检查 OSS 上是否已有文件（跳过已存在的）
    print("检查 OSS 已有文件...")
    actual_tasks = []
    for local_path, oss_key, size in tasks:
        try:
            if bucket.object_exists(oss_key):
                skipped += 1
            else:
                actual_tasks.append((local_path, oss_key, size))
        except:
            actual_tasks.append((local_path, oss_key, size))
    
    upload_total = len(actual_tasks)
    print(f"需上传: {upload_total} 个（已跳过 {skipped} 个）\n")
    
    if upload_total == 0:
        print("所有文件已存在 OSS，无需上传。")
        return
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(upload_file, bucket, p, k, s): k
            for p, k, s in actual_tasks
        }
        for future in as_completed(futures):
            pass
    
    elapsed = time.time() - start_time
    mb = uploaded_bytes / (1024 * 1024)
    
    print(f"\n{'=' * 65}")
    print(f"上传完成！")
    print(f"  新上传: {completed} 个 ({mb:.1f} MB)")
    print(f"  已跳过: {skipped} 个（已存在）")
    print(f"  失败:   {failed} 个")
    print(f"  用时:   {elapsed:.0f}s  ({mb/elapsed:.1f} MB/s)" if elapsed > 0 else "")
    
    if failed > 0:
        print(f"\n提示：{failed} 个文件失败，重新运行可继续上传")
    else:
        print(f"\n✓ 数据集已上传到: oss://{BUCKET_NAME}/{OSS_PREFIX}")

if __name__ == '__main__':
    main()
