#!/bin/bash
curl -s -X POST 'http://127.0.0.1:8100/api/v2/tenants/default_tenant/databases/default_database/collections' \
    -H 'Content-Type: application/json' \
    --data '{"name":"gzh_articles","metadata":{"hnsw:space":"cosine"}}'
echo
echo "---list---"
curl -s 'http://127.0.0.1:8100/api/v2/tenants/default_tenant/databases/default_database/collections'
