# The real OpenAI model client

The real model client is `OpenAIModelClient` in `veil/adapters/openai/`. It satisfies the `ModelClient` interface of the Engine (ticket GR-20). The Engine does not change. It supports OpenAI only.

## What we decided

- **The Responses API.** The client calls `POST /v1/responses`. The Engine writes chat messages. The client turns them into items. A system or user message stays a message. A call of the model becomes a `function_call` item. A tool answer becomes a `function_call_output` item with the same `call_id`.
- **Two parts.** `OpenAIModelClient` does the conversion. It talks to the API through the small `OpenAIApi` interface. The interface has a real HTTP adapter (`HttpOpenAIApi`) and a test stub. So the seam is real.
- **Tools.** The client sends each tool with `strict: false`. Without it, the API changes the schema when it can. The Engine checks the arguments itself.
- **No state.** Each call sends the whole conversation with `store: false`. Nothing stays at OpenAI. The client sends a call without the `id` of the API, so the API asks for no reasoning item.
- **Tokens.** The tokens come from `usage.total_tokens` of the reply. If that field is missing, the client adds the input and output tokens. If the reply has no usage, the client raises an error. It never counts zero, because that would break the run budget.
- **Tool calls.** The client copies `call_id` of the API into `ToolCall.id`. The model writes the arguments as JSON text. If the text is not a JSON object, the client gives the call with no arguments. The Engine then answers the bad call with an error text, and the model can try again.
- **Replies with no call.** A reply with text and no call has no tool calls. The Engine counts it as an empty step. The client does not read the text. An incomplete reply still gives its calls and tokens. A reply with the status `failed` is an error.
- **The key.** The Shell passes the key as a `SecretStr`. It goes in the Authorization header and nowhere else. The adapter hides it in every error. The adapter needs https. Only a local host may use http, so that tests can run against a local server. It never follows a redirect. A tool message that answers no call is an error before any call goes out.
- **Errors.** The adapter raises `ModelClientError` (in `engine/errors`). `run()` still stops on it, as ADR 0005 accepts. The error has a `retryable` flag. It is True after a rate limit (429), a time-out (408), a conflict (409) or a server error (500 or more). It is also True for a call that got no answer. A failed reply with the code `server_error` or `rate_limit_exceeded` is True too. The code `insufficient_quota` is always False, even when the status is 429.
- **Time-out.** One call can wait 120 seconds. A model call is slow.
- **Retry.** The adapter does not retry. A Shell can retry through Temporal and read `retryable`. See the accepted gap below.

## What we accept for now

- **A retry in Temporal is weak for the model.** A Temporal retry of the whole activity runs the Engine again. It repeats the model calls that already ran and used tokens. It also starts a new run report. So the count of tokens starts at zero, and the token ceiling no longer limits the whole run. A rejected call (429 or 5xx) costs no tokens. A retry of that one call inside the client costs less and keeps the ceiling. We leave the client without a retry for now. Add a bounded retry to the client before the Service Shell retries a whole run.
- A failed call that got no answer counts as retryable. A bad certificate or a name that does not resolve will fail again. The client cannot tell them apart.
- The time-out is the wait of one read on the socket. It is not a limit for the whole call.
- A reply with the status `failed`, and a call that timed out after the model ran, add no tokens to the run. The tokens are lost.
- An incomplete reply with no call looks like an empty step. The client drops the reason, for example `max_output_tokens`.
- **No reasoning items.** The client does not send reasoning items of earlier turns back. A reasoning model can work worse for this reason. The Engine messages have no place for them.
- **One choice.** The client reads the output items of one reply. It does not set a temperature, a token limit or a tool choice.
- The test answers follow the public API reference and the function calling guide. They are not recorded from a live call. See the manual check below.
- The key has the access that the Shell gives it. The adapter does not check the scope of the key.

## Manual check against the real API

No person did this check yet. Do it before the first real run:

1. Pass a test key to `HttpOpenAIApi`. Use a model name that your account can use.
2. Call `OpenAIModelClient.next` with a system message, a user message and the five tools of the Engine. Check that the reply has a tool call with an id that starts with `call_`.
3. Send the conversation again with the tool answer. Check that the API accepts the `function_call_output` item.
4. Check that `tokens` equals the usage of the dashboard for that call.
5. Use a wrong key. Check that the error names the status and does not show the key.
