import os
from pathlib import Path
import oss2

endpoint = "oss-cn-shenzhen.aliyuncs.com"
bucket_name = "gr00t"
prefix = "libero_object_no_noops_lerobot/"
out_dir = Path("/root/autodl-tmp/Project7/libero_object_no_noops_lerobot")

ak = os.environ["OSS_AK"]
sk = os.environ["OSS_SK"]

auth = oss2.Auth(ak, sk)
bucket = oss2.Bucket(auth, endpoint, bucket_name)

out_dir.mkdir(parents=True, exist_ok=True)

count = 0
skipped = 0
downloaded = 0

for obj in oss2.ObjectIterator(bucket, prefix=prefix):
    if obj.key.endswith("/"):
        continue

    rel = obj.key[len(prefix):]
    local_path = out_dir / rel
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if local_path.exists() and local_path.stat().st_size == obj.size:
        skipped += 1
        continue

    bucket.get_object_to_file(obj.key, str(local_path))
    count += 1
    downloaded += obj.size

    if count <= 5 or count % 50 == 0:
        print(f"downloaded {count}, skipped {skipped}, {downloaded / 1024 / 1024:.1f} MB")

print(f"done. downloaded={count}, skipped={skipped}, size={downloaded / 1024 / 1024:.1f} MB")