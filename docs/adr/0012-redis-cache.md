# The Redis cache

Redis caches the slow reads of the org-wide service (ticket GR-23, decision GR-11). The code is in `veil/adapters/redis/`. A Redis outage never stops a run. The Engine does not change.

## What we decided

- **What Redis holds.** The settings snapshot, the Jira metadata, the repo list of a GitHub installation and the shared counters of model calls. Nothing else.
- **What Redis never holds.** Installation tokens, the OpenAI key, Jira credentials, results of the eligible-ticket query, model replies and repo file contents. The cache has no method that stores any data. It has one typed class for each of the four uses above. A secret scan refuses any key or value that looks like a secret. A test searches everything in Redis for secrets after the runs.
- **One place for the keys.** `cache_keys.py` builds every key. All keys start with `veil:`. A text that may hold spaces, such as a Jira status, goes into a key as a digest.
- **The cache lifetimes are settings.** `cache_settings_ttl_seconds`, `cache_jira_metadata_ttl_seconds` and `cache_repo_list_ttl_seconds` set the life of the entries. `from_settings` builds the Jira cache, the repo list cache and the limiter from the settings. The cache refuses an entry with no lifetime. A rate counter lives for two minutes.
- **A Redis outage is a miss.** Each call has a time-out of 250 milliseconds. A failed call gives a miss and never raises. This includes a value that is not text. After a failed connection, the client leaves Redis alone for 5 seconds. So a dead Redis, or a Redis that does not answer, costs one time-out and not one for each read. The client uses Redis again when the cool-down ends. Tests stop and start a real server, and talk to a server that never answers.
- **The settings snapshot.** `CachedSettingsStore` wraps the store in PostgreSQL. Each run reads the version number from the database. That is one small read. The key holds the namespace of the deployment, the format of the entry, the version and a digest of the sorted repos. A write adds one to the version, so the old entry is stale at once. An entry also carries its version, and the cache checks it. If a write lands between the two reads, the cache stores the snapshot under its own version. A bad entry is a miss. Two deployments that share one Redis use two namespaces, for example `staging` and `production`.
- **The Jira metadata.** The Jira adapter has a cache seam, `MetadataCache`. The default keeps nothing. `RedisJiraMetadataCache` is the Redis version. It caches the custom field ids, which every search reads. It also caches the transitions, which every status change reads. A transition list is for one project, one issue type and one current status, because each issue type can have its own workflow. A ticket whose answer has no issue type never uses the cache. The status of a ticket is always read live.
- **When a cached transition is wrong.** If Jira says that a move is not valid (status 400, 404 or 409), the adapter forgets the list, reads Jira once and tries again. Any other failure is not retried, so a move that may have worked is never sent twice. The adapter keeps the transition list only after a move that worked. A cached list keeps only the id and the target of each transition. The refusal to close a ticket applies to cached transitions too. We do not cache status ids or label lists, because nothing reads them.
- **The repo list.** `RepoListCache.get_or_load(installation_id, loader)` keeps the list in the order that GitHub gave it. It does not keep an empty list, because a new installation may get repos soon. It does not keep a list with a name that is not `owner/name`. The caller always gets the list that the loader gave. The Service Shell calls it.
- **The rate limit.** `ModelCallLimiter` counts the calls of each minute in one shared counter. A call over the limit waits for the next minute. The limit is the setting `model_calls_per_minute`. If Redis is down, each worker counts alone against a smaller limit. That limit is the shared limit divided by `max_concurrent_runs`, rounded up, and at least 1. So the workers together stay near the shared limit. The threads of one worker share the local count with a lock. GR-28 puts the limiter around the OpenAI client.
- **The counters.** The client makes a counter with `SET key 0 EX seconds NX` and then `INCR`, in one transaction. A key that has no lifetime gets one. This needs Redis 2.6.12 or later.
- **No adapter uses another adapter's cache.** The Redis adapter imports only the snapshot model of the PostgreSQL adapter. No other adapter imports the Redis adapter. The Shell joins them. Contracts in `pyproject.toml` check this.
- **The Redis URL is a credential.** The Shell passes it. It is never a setting.
- **Tests.** The tests run against a real Redis server. The fixture starts a throwaway server from the `redis-server` program, or uses the URL in `VEIL_TEST_REDIS_URL`. Without either, the tests skip. CI sets `VEIL_REQUIRE_TEST_SERVICES`. Then a missing server fails the run, and the tests of a stopped server cannot skip in silence.

## What we accept for now

- Each run still reads the version from PostgreSQL. The cache saves the read of all rows. A database outage still stops the run.
- A fixed window allows a burst at the edge of two minutes. In the worst case, a worker makes twice the limit in a short time.
- The local limit assumes at most `max_concurrent_runs` workers. More workers can pass the limit while Redis is down.
- A call that waits for the next minute still adds one to the counter of its minute. `acquire` has no time limit. It waits at most one minute for each turn.
- A Redis that answers slower than 250 milliseconds counts as down.
- The clocks of the workers set the window. A skew of some seconds moves the edge of a window.
- A cached list of custom field ids can be old for one lifetime. If an admin makes the custom fields later, or renames one, `open_tickets` misses them until the entry ends. The cache keeps an empty list too.
- A cached transition list can be old for one lifetime. If Jira gives a transition id a new meaning in that time, a move can go to another status. The adapter checks the category in the cached list, not the real target. A short lifetime for the Jira metadata keeps this small. The retry covers only a move that Jira calls not valid.
- The secret scan of the cache uses the patterns of the Engine. It does not know a password in an address, a JWT or a Jira token of another form.
- The limiter has no wiring to the OpenAI client yet (GR-28), and no Shell uses the caches yet (GR-25).
- No test ran against ElastiCache or against a Redis with a password or TLS. The URL scheme `rediss://` passes through the Redis library.
- The tests need a `redis-server` program on the machine, or `VEIL_TEST_REDIS_URL`.
