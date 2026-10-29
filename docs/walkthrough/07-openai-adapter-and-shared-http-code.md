# The OpenAI adapter and the shared HTTP code

This part covers the real model client. An adapter is a part that talks to an outside service. The OpenAI adapter lets the Engine talk to the OpenAI Responses API. This part also covers the shared HTTP code. The GitHub adapter, the Jira adapter and the OpenAI adapter all use it. The shared code gives the three adapters the same safety rules.

## The flow

1. The Engine (see part 02, the Engine) holds a chat. The chat is a list of messages. Each message has a role such as system, user, assistant or tool. The Engine calls `OpenAIModelClient.next` in `client.py`. It gives the messages, a model name and the tool definitions. `OpenAIModelClient` satisfies the `ModelClient` interface (see part 04, the ModelClient interface, ModelReply and ToolCall).
2. `next` calls `_items`. `_items` turns the chat messages into items of the Responses API. A system or user message stays a message. An assistant text stays a message. Each tool call of the model becomes a `function_call` item. Each tool answer becomes a `function_call_output` item with the same call id.
3. `_items` remembers the id of every call that the model made. A tool message that answers an unknown call raises a `ModelClientError` before any request goes out.
4. `next` calls `_tool` for each tool definition. `_tool` builds the tool entry for the API. It sets `strict` to false, so the API does not change the schema. The Engine checks the arguments itself.
5. `next` gives the model name, the items and the tools to `create_response` of the `OpenAIApi` interface. The interface is in `api.py`. The real implementation is `HttpOpenAIApi` in `http_api.py`. A test can use a stub instead. So the seam between the two parts is real.
6. When `HttpOpenAIApi` starts, it calls `require_https` from `json_http.py`. `require_https` refuses a URL that does not use https. A local host may use http, so tests can run against a local server.
7. `create_response` calls `call_json` from `json_http.py`. It sends a POST to `/v1/responses`. The body holds the model, the input items, the tools and `store` set to false. So OpenAI keeps nothing. The key goes in the Authorization header only. One call can wait 120 seconds.
8. `call_json` opens the request through `open_without_redirect` in `no_redirect.py`. If the server answers with a redirect, the call fails. The credentials never go to another host.
9. If the call fails, `call_json` hides the credential values in the message with `redact`. It then raises the error that the adapter chose. For OpenAI, `_failed_call` makes that error. `_failed_call` sets `retryable` on the `ModelClientError`. The flag is true after a time-out (408), a conflict (409), a rate limit (429) or a server error (500 or more). It is also true for a call with no answer. It is false when the message holds the code `insufficient_quota`.
10. If the call works, `_parse` reads the reply. A reply with the status `failed` raises a `ModelClientError`. The error is retryable only for the codes `server_error` and `rate_limit_exceeded`. The message hides the key.
11. `_parse` keeps only the `function_call` items of the output. Each one becomes an `ApiFunctionCall`. `_parse` skips text items. A reply with text and no call has no tool calls. The Engine counts it as an empty step.
12. `_parse` calls `_tokens`. `_tokens` reads `total_tokens` of the usage. If that field is missing, it adds the input and output tokens. If the reply has no usage, it raises an error. It never counts zero, because zero would break the Token ceiling.
13. `_parse` returns an `ApiResponse`. It holds the calls and the token count. If the reply has an unexpected shape, `create_response` raises a `ModelClientError` that is not retryable.
14. Back in `next`, each `ApiFunctionCall` becomes a `ToolCall`. The id of the `ToolCall` is the call id that the API gave. The arguments come from `_arguments`.
15. `_arguments` reads the JSON text that the model wrote. If the text is not valid JSON, or is not a JSON object, it gives an empty dictionary. The Engine then answers the bad call with an error text. The model can try again.
16. `next` returns a `ModelReply` with the tool calls and the token count.
17. The GitHub adapter (see part 05) and the Jira adapter (see part 06) call the same `call_json` and `require_https`. They pass `plain_error` as the error maker. So all three adapters use https only, never follow a redirect and hide credential values in errors.

## Files

### src/veil/adapters/openai/client.py

This file holds the model client. It turns Engine messages into API items and the API reply into a `ModelReply`. It is its own file so the Engine sees one small class and no HTTP code.

* `OpenAIModelClient` — the real model client class. It keeps no state. The Engine sends the whole chat on each call.
* `OpenAIModelClient.__init__(api)` — stores the `OpenAIApi` object that the client will use. It takes the API object. It returns nothing. The Shell calls it.
* `OpenAIModelClient.next(messages, model, tools)` — asks the model for the next step. It takes the chat messages, a model name and the tool definitions. It returns a `ModelReply` with tool calls and the token count. The Engine calls it.
* `_tool(tool)` — builds the API entry for one tool. It sets the type to `function` and `strict` to false. It copies the name, the description and the parameters. It returns a dictionary. `next` calls it.
* `_items(messages)` — turns chat messages into items. It leaves a call without the id of the API, so the API asks for no reasoning item. It raises `ModelClientError` for a tool message that answers no call. It returns a list of items. `next` calls it.
* `_arguments(written)` — reads the JSON text of the tool arguments. It takes the text. It returns a dictionary. It returns an empty dictionary for bad text or for JSON that is not an object. `next` calls it.

### src/veil/adapters/openai/api.py

This file lists the methods that the model client needs from the API. A Protocol is a list of methods that a part must have. It is its own file so the client and the HTTP code do not depend on each other.

* `OpenAIApi` — the Protocol. It says what any OpenAI API object must offer.
* `OpenAIApi.create_response(model, input_items, tools)` — sends the items and the tools. It takes a model name, a list of items and a list of tools. It returns an `ApiResponse`. It raises `ModelClientError` when the API gives no usable reply. `OpenAIModelClient.next` calls it.

### src/veil/adapters/openai/http_api.py

This file talks to OpenAI over HTTP. It is its own file so a test can replace it with a stub.

* `HttpOpenAIApi` — the real API object. Each call is stateless. It stores nothing at OpenAI.
* `HttpOpenAIApi.__init__(api_key, base_url, timeout_seconds)` — checks the URL with `require_https` and stores the key, the base URL and the time-out. The key is a `SecretStr`, which is a value that hides itself when printed. The defaults are the OpenAI URL and 120 seconds. It raises `ModelClientError` for a URL that is not https and not local.
* `HttpOpenAIApi.create_response(model, input_items, tools)` — sends the request with `call_json` and parses the reply. It takes the model name, the items and the tools. It returns an `ApiResponse`. It raises `ModelClientError` for a reply in an unexpected shape.
* `_parse(reply, key)` — reads one decoded reply. It takes the reply and the key. It raises for a `failed` status, for an output that is not a list and for arguments that are not text. It returns an `ApiResponse`. `create_response` calls it.
* `_tokens(reply)` — finds the token count. It takes the reply. It returns the total, or the sum of the input and output tokens. It raises `ModelClientError` when the reply has no usable usage. `_parse` calls it.
* `_failed_call(message, status)` — makes the error for a failed call. It takes the message and the HTTP status. It returns a `ModelClientError` with `retryable` set. `call_json` calls it.

### src/veil/adapters/openai/models/api_function_call.py

This file holds one function call from a reply. A pydantic model is a checked record.

* `ApiFunctionCall` — a frozen pydantic model. Its fields cannot change after creation.
* `ApiFunctionCall.call_id` — the id that the API gave to the call. The client copies it into `ToolCall.id`.
* `ApiFunctionCall.name` — the name of the tool that the model wants to call.
* `ApiFunctionCall.arguments` — the arguments as JSON text, exactly as the model wrote them.

### src/veil/adapters/openai/models/api_response.py

This file holds what the client needs from one reply.

* `ApiResponse` — a frozen pydantic model.
* `ApiResponse.function_calls` — the function calls of the reply, as a tuple of `ApiFunctionCall`. It can be empty.
* `ApiResponse.total_tokens` — the tokens that the API counted for the call. It must be zero or more.

### src/veil/adapters/openai/constants/http.py

* `API_URL` — the base URL of OpenAI, `https://api.openai.com`.
* `RESPONSES_PATH` — the path of the Responses API, `/v1/responses`.
* `MODEL_CALL_TIMEOUT_SECONDS` — the wait of one model call, 120 seconds. A model call is slow.
* `RETRYABLE_STATUSES` — the HTTP statuses 408, 409 and 429. A retry can help after these.
* `SERVER_ERROR_STATUS` — 500. A status of 500 or more is also retryable.
* `RETRYABLE_ERROR_CODES` — the reply codes `server_error` and `rate_limit_exceeded`. A failed reply with one of them is retryable.
* `PERMANENT_ERROR_CODES` — the reply code `insufficient_quota`. A retry cannot help, even when the status is 429.

### src/veil/adapters/openai/constants/items.py

* `FUNCTION_CALL` — the item kind `function_call`. It marks a call of the model in the input.
* `FUNCTION_CALL_OUTPUT` — the item kind `function_call_output`. It marks a tool answer in the input.
* `FUNCTION_TOOL` — the tool type `function`.
* `ROLE_ASSISTANT` — the role `assistant` of Engine messages.
* `ROLE_TOOL` — the role `tool` of Engine messages.
* `OUTPUT_FUNCTION_CALL` — the output item kind `function_call`. `_parse` keeps only these items.
* `STATUS_FAILED` — the reply status `failed`. It means the API could not finish the reply.

### src/veil/adapters/openai/constants/messages.py

* `NO_USAGE` — the error text "OpenAI gave no usage, so the tokens are not known." `_tokens` raises it.

### src/veil/adapters/json_http.py

This file holds the code that all three adapters share to call a JSON API. It is its own file so the safety rules live in one place.

* `plain_error(error)` — makes an error maker for a caller that does not need the HTTP status. It takes an error class. It returns a function that builds that error from the message and drops the status. The GitHub adapter and the Jira adapter call it.
* `plain_error` returns a nested helper, an unnamed `lambda`. It takes the message and the status. It returns `error(message)`.
* `require_https(url, error, service)` — refuses a URL that does not use https. It takes the URL, an error class and a service name. It raises the error with a message that names the service. A URL with http passes only for the hosts in `LOCAL_HOSTS`. It returns nothing. Each adapter calls it when it starts.
* `call_json(service, error, secrets, base_url, method, path, headers, params, body, timeout)` — calls a JSON API. It builds the URL from the base URL and the path, adds query parameters and sends the body as JSON. It returns the decoded reply, or None for an empty reply. Every failure raises the error that `error` makes, with the credential values in `secrets` hidden. The error gets the HTTP status, or None when there was no answer or the reply was not JSON. A reply that is not JSON also raises. An error body keeps at most 500 characters.

### src/veil/adapters/no_redirect.py

This file opens a request and refuses to follow a redirect. A redirect is an answer that sends the caller to another address. It is its own file so one rule covers every adapter.

* `_NoRedirect` — a class that tells the HTTP code never to follow a redirect.
* `_NoRedirect.redirect_request(*_args, **_kwargs)` — returns None whatever it gets. So the redirect answer becomes an HTTP error. `_NoRedirect` calls it inside the HTTP code.
* `open_without_redirect(request, timeout)` — opens a request like `urlopen`. It takes the request and a time-out. It returns the response. A redirect raises an HTTP error. `call_json` calls it.

- `_OPENER` — the one opener that `no_redirect.py` builds from `_NoRedirect`. `open_without_redirect` uses it for every call of every adapter.

### src/veil/adapters/constants/http.py

* `TIMEOUT_SECONDS` — 30. The default time-out of `call_json`.
* `LOCAL_HOSTS` — the hosts `127.0.0.1`, `localhost` and `::1`. Only these may use http.
* `ERROR_DETAIL_MAX_CHARS` — 500. The most characters of an API error body that an error message keeps.

## Things to know

* The three adapters pass the credential values to `call_json` in `secrets`. The message of every failed call goes through `redact`. So a key does not reach an error. The OpenAI adapter also hides the key in a `failed` reply.
* `_failed_call` checks `insufficient_quota` by searching the message text. It does not read a field. If the error body keeps that text, the error is never retryable.
* A call with no answer counts as retryable. A bad certificate or a name that does not resolve also counts, but a retry will fail again. A reply that is not JSON has no status, so it also counts as retryable.
* The adapter does not retry. It only sets the `retryable` flag. A retry of the whole run would repeat model calls and reset the token count. ADR 0009 accepts this gap.
* A reply with the status `failed` and a call that timed out add no tokens to the run. The tokens are lost. An incomplete reply with no call looks like an empty step. The client drops the reason.
* The client reads only function calls. It sends no reasoning items from earlier turns. It sets no temperature, no token limit and no tool choice.
