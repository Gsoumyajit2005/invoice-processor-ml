"""S3-compatible object storage adapter for Supabase Storage S3 and Cloudflare R2."""

from __future__ import annotations

import asyncio
from typing import Any

import boto3
from botocore.exceptions import ClientError


class S3Storage:
    """Async wrapper over boto3 S3 client supporting custom S3 endpoints."""

    def __init__(
        self,
        *,
        bucket: str,
        region_name: str = "auto",
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ) -> None:
        self.bucket = bucket
        self._client: Any = boto3.client(
            "s3",
            region_name=region_name,
            endpoint_url=endpoint_url or None,
            aws_access_key_id=aws_access_key_id or None,
            aws_secret_access_key=aws_secret_access_key or None,
        )

    def _put_sync(self, key: str, data: bytes, content_type: str) -> str:
        clean_key = key.lstrip("/")
        self._client.put_object(
            Bucket=self.bucket,
            Key=clean_key,
            Body=data,
            ContentType=content_type,
        )
        return clean_key

    def _get_sync(self, key: str) -> bytes:
        clean_key = key.lstrip("/")
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=clean_key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"NoSuchKey", "404"}:
                raise FileNotFoundError(key) from exc
            raise
        return resp["Body"].read()

    def _delete_prefix_sync(self, prefix: str) -> int:
        clean_prefix = prefix.lstrip("/")
        paginator = self._client.get_paginator("list_objects_v2")
        deleted = 0
        for page in paginator.paginate(Bucket=self.bucket, Prefix=clean_prefix):
            objs = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if not objs:
                continue
            self._client.delete_objects(Bucket=self.bucket, Delete={"Objects": objs})
            deleted += len(objs)
        return deleted

    def _exists_sync(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        try:
            self._client.head_object(Bucket=self.bucket, Key=clean_key)
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"NoSuchKey", "404"}:
                return False
            raise

    async def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        return await asyncio.to_thread(self._put_sync, key, data, content_type)

    async def get_bytes(self, key: str) -> bytes:
        return await asyncio.to_thread(self._get_sync, key)

    async def delete_prefix(self, prefix: str) -> int:
        return await asyncio.to_thread(self._delete_prefix_sync, prefix)

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._exists_sync, key)
