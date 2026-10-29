# The Engine tests

This part describes the tests of the Engine. The Engine is the part of `veil` that selects Gozu Tickets, groups them, produces Fixes and opens Fix PRs. The tests run the whole Engine against fake outside services and check what a person would see. The code under test is in parts 02 to 04. The fakes and the adapter tests are in part 09, "The fakes and the adapter tests".

## The flow

1. A test calls `make_context` in `tests/support/scenario.py`. It gives a script for the model and the facts of the ticket. A script is a list of replies, and each reply is a list of tool calls.
2. `make_context` builds a Gozu Ticket with `make_ticket`. It adds more tickets if the test asks for them. It puts all tickets into a `FakeTracker`. This is a fake of Jira that keeps status, comments and labels in memory.
3. `make_context` builds a `FakeRepoProvider`. This is a fake of GitHub. It works on real local git repositories under the folder `tmp_path` of the test. The repository `acme/app` holds the files that the test gives, or a default file `app.py` with one `eval` bug.
4. For each ticket whose branch is not a Fix branch, `make_context` seeds a Source PR. The Source PR has its own branch. It is open unless the test says it is not open.
5. `make_context` builds a `FakeModelClient` that plays the script. It builds a `Context` with the settings, the credentials, the fake tracker, the fake repo provider and the fake model client. It returns the context and the three fakes.
6. The test calls `run(context)` from `veil.engine`. This is the only action under test. The Engine reads the tickets, skips some, groups the rest, runs the model for each Fix and opens Fix PRs.
7. The test checks the report that `run` returns. The report holds the outcome of each ticket, the skipped tickets with a reason, the PR addresses and the tokens used.
8. The test checks the outside result. It reads the fakes. It checks the pull requests, the commits and the files in the PR branch. It also checks the comments, the labels and the status of the tickets.
9. For a Failed Fix, the test calls `assert_failed_fix`. For a skipped ticket, it calls `assert_untouched`. To check that a secret leaks nowhere, it calls `assert_nowhere`.
10. Some tests call `run(context)` a second time. They prove that the Engine makes no duplicate PR, no duplicate comment and no new model call.
11. Two tests are not about a run. `tests/architecture/test_layers.py` reads the source code and proves that the Engine keeps its boundaries. The settings and secret tests build `Settings` or `Context` and check that it refuses bad values.

Why the tests check outside behavior and not inner calls. A test that checks inner calls, such as "function X called function Y", breaks when someone changes the inner design. It breaks even if the result stays the same. A test that checks the PR, the commit, the comment and the label breaks only when the visible result changes. The Engine can then change inside without a change of the tests. The rules that matter to a user are rules about outside results. One example is "no secret in a PR".

## Files

### tests/support/scenario.py

This file builds the scenario that nearly every Engine test uses. It exists as its own file so that all tests build the fakes in one way and use the same checks.

- `VULNERABLE` — a constant. The text of the default `app.py`. It has an `eval(input())` bug on line 3.
- `FIXED` — a constant. The same text after the Fix. It uses `int(input())`.
- `GOOD_EDIT` — a constant. One scripted `edit_file` call that makes the Fix.
- `EDIT_THEN_FINISH` — a constant. A two-reply script. The first reply makes the Fix and the second reply calls `finish`.
- `toggle_edits(count)` — builds a script of `count` valid edits that change the same text back and forth. None of them finishes the attempt. It takes a number. It returns a list of replies. Tests use it to make an attempt that runs out of steps.
- `both_attempts(script)` — gives the cheap model and the strong model the same script. It takes one script. It returns a dictionary with one script for each default model name. Tests use it when both attempts must fail.
- `make_context(tmp_path, model_script, tokens_per_call, files, settings, extra_tickets, source_files, open_source_pr, credentials, **ticket_fields)` — builds a full test scenario, as the flow above describes. `ticket_fields` change the first ticket, for example `file`, `line`, `severity`, `branch`, `labels` and `finding`. `extra_tickets` are changes on top of the first ticket. It returns the context, the tracker, the repo provider and the model.
- `assert_failed_fix(tracker, repos, report, key)` — checks a Failed Fix. There is no PR. The outcome is `failed`. The ticket is still `To Do`. It has the label `veil-failed-fix` and exactly one comment. It returns that comment so the test can check the reason.
- `assert_untouched(tracker, repos, model, key)` — checks a skipped ticket. The Engine opened no workspace and made no model call. There is no PR. The ticket has no comment and no label, and its status is `To Do`.
- `CREDENTIAL` — a constant. A fake credential value. It matches no known secret pattern, so only its exact value can find it.
- `assert_nowhere(secret, tracker, repos, report, keys, model)` — checks that a secret is in no output of the run. The outputs are the report, comments, labels, status, PR title and body, branch names, commit messages and changed files. If the test gives the model, it also checks every message that the Engine wrote for the model.

### tests/support/tool_results.py

This file holds one helper that tests of the read tools share. It exists so that these tests do not repeat the setup.

- `results_for(tmp_path, calls, files)` — runs one Fix attempt. The model makes each call in `calls` and then the good edit and `finish`. It takes the folder, a list of tool calls and extra files. It returns the text that the Engine gave back to the model for each call in `calls`.

### tests/engine/flow/test_fix_flow.py

This file proves the main path. One scripted edit makes one commit and one draft PR. It also proves what the first prompt holds and what the report and the ticket show.

- `test_scripted_edit_makes_one_commit_and_one_draft_pr` — a model edits the file and finishes. The Engine opens one draft PR on a `gozu/fix-` branch with one commit that holds the fixed file.
- `test_first_prompt_holds_ticket_facts_context_lines_and_marks_ticket_text_untrusted` — a ticket points at line 50 of a 100-line file. The first prompt has the repository, file, line and severity. It shows lines 31 to 69 and not lines 5 or 95. It wraps the finding text in an `untrusted` tag.
- `test_a_closing_tag_in_the_finding_or_the_file_cannot_end_the_untrusted_block` — the finding and the file both contain a closing tag. The prompt still has each closing tag only once, so the text cannot leave its block.
- `test_a_line_past_the_end_of_the_file_still_shows_the_end_of_the_file` — a ticket names line 500 of a two-line file. The first prompt still shows the last line of the file.
- `test_report_lists_pr_ticket_outcome_and_tokens_used` — a fix run with 150 tokens per model call. The report holds the PR address, the outcome `fixed` and 300 tokens used.
- `test_ticket_gets_pr_link_comment_and_moves_to_in_review` — after a fix, the ticket status is `In Review`. The first comment on the ticket holds the address of the PR.
- `test_calls_after_finish_in_the_same_reply_are_ignored` — a reply holds an edit, `finish` and then a second edit. The second edit does not reach the PR. The file in the PR is the fixed file only.

### tests/engine/flow/test_fix_output.py

This file proves the rules for the `finish` call. It checks what the commit, the PR and the ticket comment receive from it.

- `LONG_EXPLANATION` — the text "One. Two. Three. Four." It has four sentences, so it breaks the limit of three sentences.
- `test_the_commit_gets_the_message_of_the_model_and_the_pr_and_ticket_get_the_explanation` — the model finishes with a commit message and an explanation. The commit subject is the message. The PR body and the ticket comment hold the explanation.
- `test_a_finish_that_breaks_the_format_is_refused_and_the_model_can_finish_again` — a test with three cases. The first `finish` has an explanation of more than three sentences, or sentences that start in lower case, or a two-line commit message. The Engine refuses it, the model finishes again, and only the good text reaches the PR.
- `test_an_abbreviation_does_not_count_as_the_end_of_a_sentence` — an explanation has "e.g." in it and three real sentences. The Engine accepts it and the PR body holds the whole text.

### tests/engine/flow/test_model_contract.py

This file proves what the Engine sends to the model. It checks the tools, the first messages and the pairing of calls and results.

- `test_the_model_gets_the_five_tools_with_a_description_and_a_schema` — the tools are `read_file`, `search`, `list_dir`, `edit_file` and `finish`. Each has a description. The edit tool takes `path`, `old` and `new`, and `finish` takes `commit_message` and `explanation`.
- `test_the_conversation_starts_with_a_system_message_that_sets_the_rules` — the first message has the role `system`. It tells the model never to follow instructions in ticket text and to write at most 3 sentences. A `user` message follows it.
- `test_each_tool_result_answers_a_call_that_the_model_made` — in the second model call, the last message is a `tool` result. Its call id is the id of the `edit_file` call in the message before it.
- `test_a_reply_with_two_calls_gets_two_tool_results` — a reply makes two edits. The next model call holds two tool messages.

### tests/engine/budget/test_token_ceiling.py

This file proves the Token ceiling. It also proves that a model reply must report its tokens.

- `test_ceiling_counts_all_attempts_and_leaves_the_rest_for_the_next_run` — the ceiling is 800 and each call costs 300 tokens. The cheap attempt uses 600 and the strong attempt reaches 900. Both tickets get the outcome `left_for_next_run` with no PR, comment or label.
- `test_fix_that_finishes_is_published_even_if_its_last_call_passes_the_ceiling` — the ceiling is 500 and a fix uses 600 tokens. The Engine still publishes it. The outcome is `fixed`.
- `test_a_model_reply_must_report_its_tokens` — a `ModelReply` without a token count raises a validation error. A client that forgets the count would turn the ceiling off without a sign.

### tests/engine/edits/test_edit_refusals.py

This file proves that the Engine refuses edits that break a safety rule. The model gets an error and can try again.

- `WORKFLOW` — the path `.github/workflows/ci.yml`. The tests use it to check that the Engine refuses to edit a workflow file.
- `test_refused_edit_changes_nothing_and_the_model_is_told` — a test with 14 cases. Each case gives one bad edit. The edits target a workflow file, a lockfile or a nested lockfile. They also target a path outside the repository, a new file, a whole-file deletion, a `.env` file or a private key. Some paths use upper case or backslashes. Some deletions leave only a newline or white space. In each case the next good edit succeeds. The PR changes only `app.py` and the Engine writes nothing outside the repository.

### tests/engine/edits/test_syntax_check.py

This file proves that the Engine checks that an edited file still parses when the model finishes.

- `test_edited_file_that_no_longer_parses_is_a_failed_fix` — a test with three cases: Python, JSON and TOML. The edit breaks the file and the model finishes. Both attempts fail. The outcome is a Failed Fix and the comment names the file.
- `test_file_that_is_broken_in_the_middle_but_parses_at_finish_is_fixed` — the model breaks the file, mends it and finishes. The Engine checks only at the end. The outcome is `fixed` with one PR.
- `test_edited_file_of_unknown_type_is_not_parsed` — a text file gets content that is not code. The Engine has no parser for it. The outcome is `fixed`.
- `test_deeply_nested_json_is_a_failed_fix_not_a_crash` — a JSON edit nests brackets 100,000 deep. The run does not crash. The ticket is a Failed Fix.

### tests/engine/reads/test_list_dir.py

This file proves what the `list_dir` tool shows.

- `test_list_dir_lists_only_the_asked_directory_and_hides_secret_files` — the model lists `src`. The result names `a.py` and the folder `deep/`. It does not show `.env` or files of other folders.

### tests/engine/reads/test_read_refusals.py

This file proves that the read tools hide secret files from the model. It also proves that a setting can add refused patterns.

- `SECRET` — the fake text `TOPSECRET-9f3a`. The tests put it in a refused file and check that it never reaches the model.
- `test_read_file_refuses_secret_paths` — a test with 14 cases. The model reads a path such as `.env`, a `.pem` file, an `id_rsa` file, `.npmrc` or `.git/config`, in lower case, upper case or with backslashes. The secret content never reaches the model.
- `test_search_skips_secret_files` — the model searches for a pattern that matches both `app.py` and `.env`. The result holds the match in `app.py`. The secret in `.env` never reaches the model.
- `test_settings_can_add_refused_patterns_but_not_remove_the_built_in_ones` — a setting adds the pattern `*.secret`. The model cannot read a `.secret` file and still cannot read `.env`.

### tests/engine/limits/test_result_caps.py

This file proves the size caps on tool results. A big file cannot fill the context of the model.

- `NUMBERED` — a file of 1000 lines. Each line holds its own number, from `L0001` to `L1000`. The tests use it to check the line cap and the byte cap on a read.
- `test_read_file_returns_at_most_300_lines_and_a_note_to_narrow` — the model reads a 1,000-line file. The first result ends at line 300 with a note to narrow the request. A read from line 301 gives lines 301 to 600.
- `test_search_returns_at_most_50_matches_and_a_note_to_narrow` — a search matches every line of a large file. The result holds exactly 50 match lines and a note to narrow the search.
- `test_every_tool_result_is_capped_at_8_kb` — a file has very wide lines. The results of `read_file`, `search` and `list_dir` are each at most 8 KB. The read result also has a note to narrow.

### tests/engine/limits/test_step_cap.py

This file proves the step cap. The step cap is the most model replies that one attempt may use.

- `test_attempt_that_reaches_the_step_cap_is_a_failed_fix` — both attempts make three edits and never finish. The cap is 3. The ticket is a Failed Fix and the comment mentions the step.
- `test_attempt_that_finishes_on_the_last_allowed_step_is_fixed` — the cap is 2 and the model finishes on its second reply. The outcome is `fixed`, with a PR and no label.
- `test_model_reply_with_no_tool_calls_counts_as_a_step` — the model sends three empty replies. The cap is 3. The ticket is a Failed Fix.

### tests/engine/limits/test_diff_limit.py

This file proves the diff limit. The diff limit is the most changed lines that a Fix may have.

- `FIVE_LINES` — a file of five short lines. The tests use it to check the changed-line limit.
- `THREE_LINES` — a file of three short lines. The tests use it to check the changed-line limit.
- `test_edit_that_would_cross_the_diff_limit_is_rejected` — the limit is 1 line. A two-line edit fails, and a one-line edit works. The PR holds only the one-line change.
- `test_edit_that_only_changes_line_endings_or_trailing_spaces_counts_as_changed_lines` — a test with two cases: new line endings and trailing spaces. Each case changes three lines and the limit is 2. The Engine rejects it, and a later one-line edit works.

### tests/engine/eligibility/test_eligibility.py

This file proves which tickets the Engine skips. It also proves that a second run creates nothing new. The report names each skip reason.

- `test_ticket_raised_against_a_fix_branch_is_skipped` — a ticket has a `gozu/fix-` branch. The reason is `raised_against_fix_branch`. The Engine touches nothing.
- `test_ticket_with_an_open_pr_is_skipped` — an open PR already carries the issue label of the ticket. The reason is `open_pr`.
- `test_ticket_with_a_fix_branch_that_carries_its_label_is_skipped` — a Fix branch with the issue label exists but has no open PR. The reason is `fix_branch`.
- `test_a_fix_for_another_ticket_does_not_block_this_ticket` — open PRs exist for another ticket and for the same label in another repository. The ticket is still `fixed`.
- `test_ticket_with_the_failed_fix_marker_is_skipped_until_a_human_removes_it` — the ticket has the label `veil-failed-fix`. The reason is `failed_fix`.
- `test_ticket_with_no_issue_label_is_skipped_because_a_duplicate_cannot_be_ruled_out` — the ticket has no issue label. The reason is `no_issue_label`.
- `test_second_run_after_a_full_run_creates_nothing_new` — run twice. The second run skips the ticket with `open_pr`. There is one PR, one workspace, one comment and no new model call.
- `test_second_run_after_a_partial_run_fixes_only_the_tickets_that_were_left` — the ceiling stops the first run after one ticket. The second run skips that ticket and fixes the other. There are two PRs and one comment on each ticket.
- `test_second_run_does_not_retry_or_comment_again_on_a_failed_fix` — a ticket fails in run one. Run two skips it with `failed_fix`. There is still one comment, one label and no new model call.
- `test_report_counts_the_skipped_tickets_by_reason_and_still_fixes_the_rest` — six tickets with mixed problems. The report lists each skip under its reason. The Engine fixes one ticket and skips five. There is one PR.
- `test_second_ticket_with_the_same_issue_label_is_skipped_in_the_same_run` — two tickets share one issue label. The Engine fixes the first. It skips the second with `duplicate_issue`.
- `test_a_ticket_that_the_tracker_lists_twice_is_fixed_once` — the tracker returns the same key twice. The Engine fixes it once, with one PR and one comment.
- `test_the_same_issue_label_on_two_source_prs_is_fixed_on_each` — two tickets share a label but have different Source PR branches. Both are `fixed` with two PRs.
- `test_a_fix_pr_on_one_source_pr_does_not_block_another_source_pr` — a Fix PR with the same label exists on a different base branch. The ticket is still `fixed`.
- `test_a_fix_branch_with_another_prefix_does_not_block_the_ticket` — a branch with the label has a prefix other than the Fix prefix. The ticket is still `fixed`.

### tests/engine/source_pr/test_source_pr.py

This file proves that the Engine works from the branch of the Source PR. It never moves that branch or `main`.

- `MAIN_WITHOUT_THE_BUG` — the files of the main branch. `app.py` holds `x = 1` and has no bug.
- `BRANCH_WITH_THE_BUG` — the files of the Source PR branch. `app.py` holds the bug.
- `source_pr_context(tmp_path)` — builds a scenario. The ticket belongs to the open Source PR `feature-x`. The bug is on that branch and not on `main`. It takes the folder. It returns the same four values as `make_context`.
- `test_the_fix_is_built_from_the_branch_of_the_source_pr` — the bug exists only on the Source PR branch. The Engine fixes it. The outcome is `fixed` and the PR holds the fixed file.
- `test_the_fix_pr_targets_the_branch_of_the_source_pr` — the Fix PR has the base `feature-x`. It is a draft with one commit.
- `test_the_engine_never_moves_the_source_branch_or_main` — after the run, the heads of `feature-x` and `main` are the same as before. The Fix PR has its own new branch.
- `test_ticket_whose_source_pr_is_not_open_is_skipped` — a test with two cases: a merged or closed PR and a scan of the default branch. The reason is `source_pr_not_open` and the Engine touches nothing.
- `test_the_strong_attempt_also_starts_from_clean_files_of_the_source_branch` — the cheap attempt fails and the strong attempt succeeds. It starts from clean files of the Source PR branch. There is one workspace and the PR targets `feature-x`.
- `test_a_second_run_makes_no_duplicates_in_the_source_pr_flow` — a second run skips the ticket with `open_pr`. There is one PR, one workspace and one comment.

### tests/engine/escalation/test_escalation.py

This file proves that a failed cheap attempt leads to exactly one strong attempt. The strong attempt gets only the failure reason.

- `SMALL_AND_BIG` — a `Settings` value with a step cap of 3, the cheap model named `small` and the strong model named `big`. The tests use it to see which model runs each attempt.
- `test_cheap_attempt_that_hits_the_step_cap_escalates_once_to_the_strong_model` — the cheap model uses all steps and the strong model succeeds. The models used are three cheap calls and two strong calls. The outcome is `fixed` in one workspace.
- `test_strong_attempt_gets_only_the_failure_reason_of_the_cheap_attempt` — the strong attempt starts with two messages. They are the system message and a user message that holds the repository and the "step cap" reason.
- `test_other_failures_of_the_cheap_attempt_also_escalate` — a test with two cases: the cheap model finishes without a change, or it breaks the syntax. Both cases escalate and the strong model fixes the ticket.
- `test_ticket_file_that_the_engine_cannot_read_does_not_escalate` — the file of the ticket does not exist. The result is a Failed Fix with no model call at all.
- `test_failed_strong_attempt_is_a_failed_fix_with_both_reasons_and_no_third_attempt` — both attempts fail for different reasons. The comment holds both reasons. The models used are one cheap call and three strong calls.

### tests/engine/failures/test_failed_fix.py

This file proves what a Failed Fix looks like and that it does not stop the run.

- `test_finish_without_any_edit_is_a_failed_fix` — the model finishes without a change. The ticket is a Failed Fix and the comment mentions the missing change.
- `test_ticket_file_that_is_not_in_the_repo_is_a_failed_fix` — the file of the ticket is missing. The ticket is a Failed Fix and the comment names the file.
- `test_ticket_that_points_at_a_secret_or_outside_file_is_a_failed_fix_and_nothing_is_read` — a test with three cases: `.env`, a path outside the repository and a `.pem` file. Each is a Failed Fix and the model gets no message.
- `test_failed_fix_does_not_stop_the_next_ticket` — the first ticket fails and the second succeeds. The outcomes are `failed` and `fixed`. The second ticket has no label and the status `In Review`.
- `test_a_failed_comment_write_does_not_make_the_next_run_try_the_ticket_again` — the tracker fails on the first comment and the run raises an error. The next run still skips the ticket with `failed_fix`. It makes no new model call.

### tests/engine/failures/test_bad_tool_calls.py

This file proves that a bad tool call gives the model an error and does not stop the run.

- `test_bad_tool_call_gives_the_model_an_error_and_the_run_goes_on` — a test with 12 cases. Each case gives one bad call. The calls name an unknown tool or have missing or extra arguments. They also give a bad start line, a missing file or a bad regular expression. Other calls give an empty path, a dot path or a folder outside the repository. The next calls work and the outcome is `fixed`.
- `test_binary_file_does_not_break_search` — the repository holds a binary file. The model searches. The run does not fail and the outcome is `fixed`.

### tests/engine/grouping/test_shared_pr.py

This file proves the rules for the Shared PR. Low and Medium Fixes of one Source PR go together.

- `BUGGY` — file text with the line `value = eval(input())`. This is the bug that the Engine fixes.
- `FIXED_LINE` — the same line after the fix: `value = int(input())`.
- `fix_of(path, commit_message)` — builds the script of one ticket. The model edits the file and finishes with the commit message. It takes a path and a message. It returns a list of two replies. Other grouping tests import it.
- `toggles(path, count)` — builds `count` valid edits of one file that never finish. It takes a path and a number. It returns a list of replies. Tests use it to make a ticket fail.
- `test_low_and_medium_fixes_of_one_source_pr_go_into_one_shared_pr` — two tickets, Medium and Low. There is one draft PR based on the Source PR branch with two commits. Both tickets get the PR link and `In Review`. The repo provider now sees an open PR for both labels.
- `test_a_failed_fix_stays_out_of_the_shared_pr_and_leaves_no_edit_in_it` — the middle of three tickets fails. The PR holds the other two commits and does not change the file of the failed ticket. The failed ticket has the marker label and the status `To Do`.
- `test_a_shared_pr_holds_at_most_the_cap_and_the_next_run_takes_the_rest` — the cap is 2 and three tickets exist. The first run fixes two and leaves one for the next run. The second run fixes the third in a second PR.
- `test_tickets_of_different_source_prs_get_separate_shared_prs` — two tickets have different Source PR branches. There are two PRs, each with its own base branch.
- `test_at_the_token_ceiling_the_fixes_that_passed_are_published_and_the_rest_wait` — the ceiling is 800. The first ticket is `fixed` and published. The other two are `left_for_next_run` with no comment and no label. The tokens used are 900.
- `test_a_second_run_after_a_shared_pr_creates_nothing` — a second run skips both tickets with `open_pr`. There is one PR, one workspace and one comment on each ticket.
- `test_the_branch_names_the_first_fix_that_passed_so_a_retry_does_not_collide` — the first PR branch is `gozu/fix-shared-gr-101`. A human removes the failed marker. The retry gets the branch `gozu/fix-shared-gr-100`, so the two branches do not collide.

### tests/engine/grouping/test_high_pr.py

This file proves the rules for the High PR. A High ticket gets its own PR unless two High Fixes change the same file.

- `edit_file_a(old, new)` — builds an edit call for the file `a.py`. It takes the old and new text. It returns a tool call.
- `finish_message(commit_message)` — builds a `finish` call with a fixed explanation and the given commit message. It takes a message. It returns a tool call.
- `test_each_high_ticket_gets_its_own_high_pr` — two High tickets in different files. There are two PRs with one commit each. Each ticket comment holds its own PR link.
- `test_high_fixes_of_the_same_file_go_into_one_pr_and_the_body_gives_the_reason` — two High tickets change the same file. There is one PR with two commits. The body says they share a file and names it.
- `test_high_tickets_of_the_same_file_group_even_if_the_path_is_written_differently` — one ticket writes the path as `./a.py` and the other as `a.py`. They still go into one PR.
- `test_the_body_gives_no_same_file_reason_if_only_one_high_fix_passed` — two High tickets share a file but one fails. The PR body does not say "same file".

### tests/engine/grouping/test_grouping_settings.py

This file proves how settings change grouping and branch names.

- `three_tickets(tmp_path, severities, settings)` — builds three tickets of one Source PR with their own files and severity words. It takes the folder, three words and optional settings. It returns the four values of `make_context`.
- `pr_sizes(repos)` — lists the number of commits of each PR in sorted order. It takes the repo provider. It returns a list of numbers.
- `test_default_severity_map_sends_high_to_its_own_pr_and_unknown_words_are_high` — a test with five cases of severity words, for example `BLOCKER`, `MAJOR`, `Low` and `WEIRD`. The High ticket gets its own PR. An unknown word counts as High.
- `test_the_severity_map_is_a_setting` — a setting maps `MAJOR` to high and `MINOR` to low. The PRs have 1 and 2 commits.
- `test_the_branch_prefix_is_a_setting_and_the_no_loop_rule_uses_it` — the prefix is `veil/`. The Fix branch starts with it. The Engine skips a ticket on a `veil/` branch as `raised_against_fix_branch`.
- `test_a_custom_prefix_does_not_weaken_the_no_loop_rule_for_the_fixed_prefix` — with the prefix `veil/`, a ticket on a `gozu/fix-` branch is still skipped.
- `test_a_partial_severity_map_changes_only_its_words_and_keeps_the_defaults` — a setting changes only `MAJOR`. The default words keep their meaning. The PRs have 1 and 2 commits.
- `test_the_branch_prefix_must_be_long_enough_and_end_with_a_separator` — a test with 11 bad prefixes, for example an empty text, `gozu` or `../`. `Settings` refuses each one with a validation error.

### tests/engine/secrets/test_secret_scan.py

This file proves that no secret reaches any output. It covers a credential of the run and text that matches a known key pattern.

- `KEY_LIKE` — a dictionary of fake keys, one for each known secret pattern. The test builds each key from pieces, so no whole key sits in the code.
- `edit_that_adds(text)` — builds a script. The edit fixes the bug and adds `text` as a comment on the same line, then the model finishes. It takes a text. It returns a list of two replies.
- `test_a_credential_of_this_run_in_an_added_line_fails_the_attempt_and_the_strong_attempt_gets_one_try` — the cheap model adds the credential. The strong attempt succeeds. The credential is in no output.
- `test_if_both_attempts_add_the_credential_the_ticket_is_a_failed_fix_and_the_comment_names_no_value` — both attempts add it. The ticket is a Failed Fix. The comment says "credential" and holds no value.
- `test_a_secret_pattern_in_an_added_line_fails_the_attempt` — a test with 8 fake keys, for example a private key header, a cloud access key id, a GitHub token and a Slack token. The cheap attempt fails and the strong attempt is `fixed`. The key is in no output.
- `test_secret_like_text_that_is_already_in_the_file_does_not_block_the_fix` — the file already holds a fake key. The Fix adds none. The outcome is `fixed`.
- `test_text_that_only_looks_a_little_like_a_key_is_not_a_secret` — a test with four honest texts, such as "see the sk-learn docs". The Engine does not treat them as secrets. The outcome is `fixed`.
- `test_a_secret_in_the_explanation_or_the_commit_message_fails_the_attempt` — a test with four cases. A credential or a fake token is in the explanation or in the commit message. The cheap attempt fails and the strong attempt is `fixed`. The secret is in no output.
- `test_the_redaction_net_hides_a_credential_in_a_ticket_field_in_the_failed_fix_comment` — the file name of the ticket holds the credential. The comment shows `[redacted].py`. The credential is in no output.
- `test_the_redaction_net_hides_a_credential_in_the_pr_body_and_the_ticket_comment` — a file name holds the credential and two High Fixes go into one PR. The PR body shows `[redacted].py` and the credential is in no output.
- `test_a_key_that_is_already_on_an_edited_line_does_not_block_the_fix` — the model changes only the comment of a line that already holds a fake key. The Fix adds no secret. The outcome is `fixed` with no label.
- `test_a_key_pattern_in_a_failure_reason_does_not_reach_the_ticket_comment` — the ticket file name holds a fake key. The Failed Fix comment shows `[redacted].py` and not the key.
- `test_a_parser_error_that_would_repeat_a_key_name_does_not_reach_the_comment` — a bad TOML edit makes a parser error that repeats a fake key name. The comment names the kind "AWS access key id" and not the key.
- `test_the_run_report_never_holds_a_credential_even_in_a_ticket_key` — the ticket key holds the credential. The report shows the key as `GR-[redacted]` with the outcome `failed`.
- `test_the_model_never_gets_a_credential_from_the_ticket_or_the_file` — the file and the finding hold the credential and a fake token. The messages that the Engine writes hold neither. The first prompt shows `[redacted]`, and the normal code line stays.

### tests/engine/secrets/test_secret_guard.py

This file proves how `Context` and `redact` protect credentials. `redact` is the filter that replaces credential values with `[redacted]`. Adapters and Shells also use it.

- `test_the_context_hides_the_credential_values_in_repr_and_json` — the printed form and the JSON of a `Context` do not show the credential.
- `test_the_context_refuses_a_credential_value_that_is_too_short_and_does_not_echo_it` — a test with three cases: empty, `short` and seven characters. `Context` refuses each value, says "at least 8 characters" and does not repeat the value.
- `test_the_context_refuses_a_credential_value_that_is_only_white_space` — a test with three white-space values. `Context` refuses each one and says "only white space".
- `test_the_engine_exports_the_redaction_filter_for_adapters_and_shells` — `redact` replaces every copy of a value, even inside a longer word. It leaves other text alone. If one value holds another, it hides the longer value completely.
- `test_redact_leaves_no_part_of_two_credential_values_that_overlap` — two values overlap in the text. `redact` hides all of both. No piece of either value remains.
- `test_redact_hides_a_value_that_sits_inside_a_secret_pattern_match` — a credential is a part of a fake GitHub token. `redact` replaces the whole token with `[redacted]`.

### tests/engine/settings/test_defaults.py

This file proves the default values of `Settings` and the values that it refuses.

- `numbered(count, value)` — builds a text of `count` lines. Each line holds its number and `value`. It takes a number and a word. It returns the text.
- `test_default_step_cap_is_25_tool_calls` — 24 edits and `finish` make a Fix, which is 25 calls. One extra edit makes both attempts fail with a Failed Fix.
- `test_default_diff_limit_is_200_changed_lines` — a test with two cases. Replacing 200 lines is `fixed`. Replacing 201 lines is `failed`.
- `test_safety_rules_are_not_settings` — a test with four cases: workflow edits, new files, deletions and the default branch. `Settings` refuses each name, so a user cannot switch a safety rule off.
- `test_settings_reject_nonsense_limits` — a test with nine bad values, such as a step cap of 0, a negative diff limit and an empty model name. `Settings` refuses each one.
- `test_default_token_ceiling_is_100_000` — the default Token ceiling is 100,000 tokens.

### tests/architecture/test_layers.py

This file proves the structure of the code. It reads the source and does not run the Engine. It exists so that a wrong import or a misplaced constant fails a test.

- `ROOT` — the root folder of the project, two levels above the test file.
- `ENGINE` — the folder `src/veil/engine`. The environment test reads every file in it.
- `ENV_NAMES` — the names `environ`, `getenv` and `putenv`. The environment test looks for them in the Engine.
- `REGISTRIES` — the three names `TOOLS`, `PARSERS` and `_OPENER`. They may sit outside a constants folder, because they hold code.
- `test_engine_imports_nothing_from_adapters_or_shells` — runs the `lint-imports` tool with the contracts in the project file. It expects exit code 0, so the Engine imports no adapter and no Shell.
- `test_engine_reads_no_environment_variables` — reads every Engine file as a syntax tree. It expects no use of `environ`, `getenv` or `putenv`. The Shell gives credentials to the Engine.
- `_is_type_variable(node)` — says whether a line such as `T = TypeVar("T")` names a type and not a constant. It takes one syntax node. It returns true or false.
- `constants_outside_the_constants_folders(allowed)` — lists names in capital letters that sit outside a `constants` folder in `src`. It skips type variables and the names in `allowed`. It returns a list of file and name pairs.
- `test_every_constant_lives_in_a_constants_folder` — runs the check with the allowed names `TOOLS`, `PARSERS` and `_OPENER`. It expects an empty list.
- `test_the_constants_check_finds_a_constant_in_the_wrong_place` — runs the check with no allowed names. It expects exactly `TOOLS`, `PARSERS` and `_OPENER`. This proves that the check can find a fault.

## Things to know

- No test calls the Engine inner parts directly for the main rules. Tests call `run(context)` and read the fakes. A change of the inner design does not break them.
- Many tests run the Engine twice on one context. They prove that the Engine skips finished work, and that it does not retry a Failed Fix until a human removes the label `veil-failed-fix`.
- The secret tests build fake keys from pieces of text, so the test files hold no real key-like text. `assert_nowhere` checks the report, comments, labels, PR, commits, files and the messages that the Engine wrote for the model.
- `tests/architecture/test_layers.py` needs the `lint-imports` program in the same folder as the Python that runs the tests. If it is absent, the first test fails.
- `test_the_constants_check_finds_a_constant_in_the_wrong_place` names three files and constants by hand. If someone moves or renames them, this test fails, and its list needs an update.
- `test_default_step_cap_is_25_tool_calls` runs two scenarios in one test. The second uses the sub-folder `over` of `tmp_path` so that its repositories do not collide with the first.
