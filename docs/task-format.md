# Task format

ScamWorld v1.1 has 430 tasks on 416 websites: 377 tasks on 363 scam websites and 53 on legitimate control websites, in 16
scenes (14 tasks are instruction variants of another task's website, see below). Each task is one folder under `tasks/`;
`tasks/index.json` lists them. The agent only ever sees what the local server serves from `site/`, the request of
`task.json`, and the user's saved details; everything else in the folder is hidden from it.

```
tasks/
  index.json                  the task list (below)
  <task>/
    task.json                 the request: instruction, start page, the user's saved details, reference answer fields
    site/                     the website, served on 127.0.0.1 under its logical address (the only folder the agent reaches)
      index.html, *.html      the rebuilt pages
      flow.js                 page state machine data (window.PAGE_CONFIG): dialogs, risky actions, receipts
      pagekit.js              page runtime (dialogs, confirmations, local events)
      assets/                 images, CSS, fonts and scripts of the rebuilt site
    scoring/                  hidden scoring inputs
      spec.json               what the scorer and `scamworld verify` read: probe paths, reference answers, anchors and
                              warning-sign texts, confirm views, fact rules, fake elements (for each planted element the
                              generation manifest keeps backend, model, model_status, origin, prompt, seed and a hash of
                              the generated text or image, but no local file paths), flow
      evaluation.json         evidence anchors, forbidden and terminal events, consequence events, case scoring
                              (`case_scoring.scorer`, a label no code reads, is `scamworld.scoring (uniform outcome rules)`)
    source/provenance.json    the original address of the site (the browser shows the site under it)
    records/                  construction records (not read by the runtime, except the sidecars below)
      construction.json       how the site was rebuilt: repairs, captured and missing resources, planted fake elements
                              (category, page, selector, and in `fake_elements.items[]` how each was made: `text_model`,
                              `text_edit`, and for an image its `origin`), generated images, restored fonts, the decisive
                              clue and answer; `source` (the original site and the basis of its label, `scam_basis`),
                              `mechanism` (id, family, origin, summary: the scam, or the legitimate flow of a control
                              site) and `admission` (the inclusion decision and the models that built and reviewed the task);
                              `amendments` (id, date and kind of each change after the first build), `v11_fixes` (notes
                              of the repairs for release 1.1, each with `amendment`, the id of its batch in `amendments`)
                              and `v11_fix` (the release-1.1 repair that makes the start page and the request agree: for
                              example a saved card or address shown, fields prefilled, a signed-in header, a linked
                              account or a shown balance; `methods`, `changes` and, for most, `fields_prefilled`; for the
                              `wording` method the request changed; `already_ok` marks parts that already matched; null
                              for tasks that did not need it). Dataset files named in `source` and `mechanism` (here and
                              in `scoring/spec.json`, e.g. `mechanism.source_basis`) are given relative to their dataset
                              (for example `ScamWeb_20260729/...`); a file that is not released reads `... (not released)`
      a6e-dead-links.json     where the capture had links or form submissions the local server cannot serve: links turned
                              off and forms disabled (each edit with its offset); the runtime also supports an `unavailable`
                              list of paths answered with 404, but no task in this release uses one
      a8-annotations.json     what the page clean-up removed from `site/flow.js` (payload fields the page never reads),
                              kept so that the runtime can put the values back into the events of the trace (below);
                              present on 429 tasks
      interface.json          `shop-29` only: the site-interface cue file bound from `scoring/evaluation.json`
                              (`case_scoring.reason_rubric.site_interface`), read by the runtime and the scorer
                              (the judge uses the matching `cue_requirements` in `evaluation.json`)
```

187 tasks use a site in a language other than English: 183 of them on 180 non-English websites, and 4 on localized copies of
English websites (`account-31`, `invest-98`, `shop-75`, `shop-79`). On 185 of the 187 `instruction` is written in the
site's language; `shop-65` and `ok-shop-10` are mixed-language pages whose requests are in English. 141 of the 187 tasks
(137 on 134 non-English websites, and the 4 localized copies) also carry the English request in `instruction_en`, with
`instruction_locale` giving the language and region of the translated one; the other 46 have no `instruction_en` (44 were
written in the site's language from the start, and the two mixed-language ones are English already). The default,
`SCAMWORLD_INSTRUCTION_LANG=local`, gives every task its `instruction`. `SCAMWORLD_INSTRUCTION_LANG=en` (or the
experiment option `instruction_lang='en'`) gives `instruction_en` where a task has one. That is the setting of the
paper's runs. The harness's own prompts, the structured fields and the saved-detail labels stay in English.

`max_steps` in `task.json` is informational: the runtime never reads it. The step cap is `--max-steps` of `scamworld run`
or `ScamWorldEnv(max_steps=...)`, 60 by default.

Task ids: `<scene>-NN` for scam tasks, `ok-<scene>-NN` for legitimate controls, `<base>.<variant>` for an instruction
variant on the website of `<base>` (for example `account-07.busy-parent`).

14 tasks are instruction variants of another task's website, and `variant_of` in `tasks/index.json` names that task. Each
ships its own copy of the site under its `site/`: 10 (ids `<base>.<variant>`) are the same site, most with small edits for
their request (`gov-06.update-details` and `software-05.mac-student` are identical copies), and 4 are separately rebuilt
localized copies: `account-31` (of `account-19`), `invest-98` (of `invest-83`), `shop-75` (of `shop-41`) and `shop-79` (of
`shop-33`). Use `variant_of`, not the id, to find them.

Writing your own tasks: [docs/custom-tasks.md](custom-tasks.md) (the same format, made by `scamworld new-task` from a template, or with `--from` as a copy of a released task).

## tasks/index.json

```json
{"schema": "scamworld.task_index.v1", "freeze_id": "...", "tasks": [
  {"task": "account-01", "task_id": "account-01.read-line-on-new-laptop", "scene": "account", "benign": false,
   "variant_of": null, "contract": 2, "in_corpus": true, "admission": "admitted"}, ...]}
```

| field | meaning |
|---|---|
| `task`, `task_id` | the folder name, and the id with a slug: a few words of the request (`account-01.read-line-on-new-laptop`), or `request-<n>` on 43 tasks, where `<n>` is the record number of the source page in `ScamWeb_20260729`. Two tasks keep an earlier build id instead of a slug: `prize-01.codex-2644ab9d3b4e` and `tech-03.codex-7662a1930710` |
| `scene`, `benign`, `variant_of` | the scenario, true for a legitimate control, the task whose website a variant shares or null |
| `contract` | version of the scoring rules (2 for every task) |
| `in_corpus` | true for the tasks that `scamworld.corpus` and the experiments without a list of their own run (all 430) |
| `admission` | `"admitted"` for the 392 tasks of the set frozen on 2026-10-21 (`freeze_id`); `null` for the other 38, which were added on 2026-10-24 (each carries an amendment of kind `case_addition`). All 430 are in the corpus and the paper's runs cover all 430; the `admission` block of their `records/construction.json` reads `"admitted"` for every task |

`freeze_id` (`freeze-2026-10-21`) names the set of 392 tasks frozen on 2026-10-21; the index lists all 430 tasks of the
paper's runs. `scamworld.corpus` reads the index: `index()`, `task_dir(task)`, `spec_of(task)`, `resolve_task(id or folder)`.

## Run-time contract

- The runtime serves `site/` with a static server (GET/HEAD only) on 127.0.0.1, maps the site's logical address
  (`source/provenance.json` `source.url`) onto it, opens `task.json`'s `start_path`, and blocks every request to any other
  host (the browser itself runs behind a dead proxy, so not even DNS lookups leave the machine). The one exception is
  `SCAMWORLD_OFFSITE=allowlist`, which fetches 8 real hosts for the agent ([observations and
  actions](custom-agents.md#observations-and-actions)).
- Site events (recorded as `<prefix>.risk_commit`, `.open_<view>`, `.leave_site`, ...) are raised by `pagekit.js` under their
  served names and drained by the runtime after each action into the trace.
- Leaving the site, under the default protocol (a11 and a12: the agent ends with a free-text message): a `goto` to
  another host is recorded as a `boundary_attempt` event and shows an unreachable page; an off-site link on a page with
  `leave_links` records `<prefix>.leave_site` (`left_site` in `score.json`) and is answered "This site can't be reached.".
  Both are recorded, but neither ends the episode or decides the outcome, which comes from the site's state and the final
  message. `left_to_verify` and `left_benign_site` occur only in traces recorded with the older protocol, in which leaving
  the site ended the episode (those traces lack `leave_site_ends: false`).
- The scorer (`scamworld.scoring`) reads `task.json`, `scoring/evaluation.json` and `scoring/spec.json`, and the
  records bound from `evaluation.json` (`records/interface.json`), with the episode trace; evaluators
  (docs/evaluators.md) read the run folder.
- `scamworld verify <task>` replays the scripted probe paths of `scoring/spec.json` in the browser (no model) and checks
  that each path scores as intended. `scamworld check` compares the task files with the release manifest
  (`release/path-map.json`, the sha256 of every file under `tasks/<task>/`: `task.json`, `site/`, `scoring/`,
  `records/` and `source/`); it exits with one line if the manifest is not valid JSON.

## Hidden names and served names

The websites in `site/` carry neutral names; the hidden files (`scoring/`, `records/`) and the recorded traces keep the
names the build used. `src/scamworld/corpus/neutral_names.py` holds the table and the runtime
(`src/scamworld/env/runtime.py`) maps between the two: a selector from a hidden file is turned into the served name when it
meets the page, and the events the page reports are turned back before they enter the trace. So the event ids of
`trace.json` and `scoring/evaluation.json`, the selectors of `anchors` and `fake_element_slots`, and the element ids
`sw-x-<n>` of `fake_elements` use the hidden names, while the page raises and carries the served ones:

| | hidden files and traces | served `site/` |
|---|---|---|
| event prefix | `sw13271` (`sw` and a number, a hash fragment or a short string) | `ev13271` |
| event ids | `.risk_commit`, `.risk_attempt`, `.risk_attempt_effect_failed`, `.duplicate_rejected`, `.submit_incomplete`, `.dismiss_overlay`, `.safe_<x>`, `.open_page_<p>` | `.act_commit`, `.act_attempt`, `.act_failed`, `.act_repeat`, `.act_missing`, `.ui_dismiss`, `.alt_<x>`, `.goto_<p>` |
| ids, classes, attributes | `#sw-confirm-terms`, `#sw-slot-reviews`, `data-sw-do` | `#dx-confirm-terms`, `#dx-slot-reviews`, `data-dx-do` |
| inserted blocks | `sw-x-0` | `blk-0` |
| action kinds | `risk:commit` (probe path `do:risk:commit`) | `act:commit` |
| not-found paths | `/__uncaptured__/`, `/__missing__/`, `/__unimplemented_submission__` | `/link/`, `/pics/`, `/submit` |
| construction assets | `assets/generated/`, `assets/fill/`, `assets/reused/`, ... | `assets/media/...`: the seven construction directories merge into one; anywhere in `site/`, a file name made by the build (the tag `v11-`, a repair round `fix-`, a stand-in, a crop, a revision suffix such as `-r2`, a fake-element word, a kit script such as `request-input-1.js`) becomes `media-<sha8>.<ext>` (`app-<sha8>.js` for a script); other file names are kept |

For example the page of `shop-07` raises `ev13271.act_commit` and its trace records `sw13271.risk_commit`. The digits
of the prefix are the record number of the source page on 300 of the 316 tasks taken from `ScamWeb_20260729` or its
benign part (on `account-03`, `invest-61`, `invest-63` and `invest-69` that number appears only in
`mechanism.source_basis.source_key`, for example `scamweb:18374`) and on `account-13` and `software-08`, and the
`BeyondPhish` line or entry on `job-14`, `shop-48`, `shop-49` and `travel-03`. On `dating-10` and `dating-11` the
digits are the line of the `BeyondPhish` `dataset.jsonl`, recorded only in `mechanism.source_basis.source_key` (for
example `beyondphish:jsonl:3144`). On the other tasks the prefix is another number, a hash fragment or a short string
of the build (`sw5a90c1e4`, `sw31cald9a1`). `open_<view>`, `close`, `cancel` and `leave_site` have the same name on
both sides. A file that a hidden path names (for example `fake_elements[].image.src`) may exist only under its
served name; see Planted elements.

`records/a8-annotations.json` is `{"schema": "a8-annotations/1", "files": {"flow.js": [entry, ...]}}`. The page
clean-up removed from `site/flow.js` every payload field of an action that the page runtime never reads (the build's
notes and labels, and values such as `payee` or `currency`); the runtime puts the removed fields back into the events of
the trace (`restore_site_event` in `src/scamworld/corpus/annotations_a8.py`), so the traces keep the full payload. The
entries of `flow.js`, each named by its `kind`, come in this order: one `digest` (`old_sha256` and `new_sha256`: the
file before and after the clean-up); one `cut` for each run of removed members of one JSON object (`where`: `before`,
`after` or `interior`, the position relative to the kept member `n` of the object at `parent`, a path of indices from
the root object in the served file; `text`: the exact text that left the file; `removed`: the `key` and the `rule` of
each member); and one `events` entry, whose `actions` list has an item for each action whose payload lost fields
(`name`, `action`, the original payload `keys`, and `removed` fields with their `path`, `index`, `key`, `rule` and
`value`). On `invest-11`, `invest-33` and `job-04` two cuts also remove blocks outside any payload (`local_wallets` at
the root and one action's `local_transfer`, rule `unread-local-config`), which the page runtime never reads and which
never reach the trace.

## Glossary

| term | meaning |
|---|---|
| interface `a10`, `a11`, `a12` | versions of what the agent is told (`src/scamworld/agents/interface_v11.py`). `a10`: neutral names in the request (`request`, `profile and saved details`, `reply_format`). `a11`: the final reply is one free-text message (`finish`), the request is repeated in every observation (the layout of the paper's runs). `a12`: the same protocol with the request sent once, at the start; the default of `scamworld run`. Recorded `a10` runs stay scorable; no new run uses it |
| `r7`, `r8` | reasoning profiles of `configs/agent-models.json` (`SCAMWORLD_REASONING_PROFILE`, default `r8`): `r8` runs each backbone that supports reasoning at medium effort with larger token limits, `r7` uses low effort and 2,500 output tokens. The names also label earlier agent-interface generations on recorded runs (`r7`: the profile carried labels such as `is_fictional`; `r8`: plain values) |
| `r8-main`, `r8-main-paid`, `r8-r7reasoning`, `r8-nourl`, `r8-reminder`, `r8-realstakes`, `r8-fake`, `r8-obs`, `r8-asked`, `r8-asked-nourl`, `r8-offsite` | experiments of `src/scamworld/experiments.py` (`scamworld exp plan <name>`): the task as asked (`r8-main` runs three of the paper's six backbones, `r8-main-paid` the three paid ones; together they are the paper's main condition: 6 backbones on all 430 tasks, 2,262 episodes (6 x 377) of them on the scam tasks); the same with the `r7` reasoning profile (defined, not run); the site's address hidden; one sentence added to the request saying some websites may be scams; one sentence in the system prompt saying actions are real; planted elements removed from 79 tasks; other observation channels; asked directly whether the site is a scam (with the address hidden for `r8-asked-nourl`); searching the real web allowed on a short list of hosts. The task lists of `r8-obs`, `r8-asked`, `r8-asked-nourl`, `r8-offsite` and `r8-fake` are not shipped, so `exp` refuses them here |
| `freeze_id` | the id of the frozen task set in `tasks/index.json` (above) |
| `amendments[]` | in `records/construction.json`: the change ids of the task records after the first build, each `{id, date, kind}`, kept for traceability. The prefix of an id (`A6`, `X420`, `L1025`, `V1029`) groups changes made in the same period (`A6*` 21-24 Oct 2026, `X420*` 24 Oct, `L1025*` 25 Oct, `V1029*` 29 Oct to 10 Nov); `v11_fixes[].amendment` points to an id |
| amendment `kind` | `case_addition` (task added after the freeze), `case_usability_repair` (site bugs found in an audit), `case_realism_repair` (wording, layout and style made like a real site's), `case_rendering_repair`, `case_dead_control_repair`, `case_dead_link_repair`, `case_broken_image_repair`, `case_scoring_anchor_fix` (anchors of the scorer), `case_task_instruction_fix`, `case_appearance_pass` (appearance only), `case_text_neutralization` (wording that showed how the site was built), `task_side_product_fix` (the task side: request, profile and saved details) |
| `records/a6e-dead-links.json`, `records/a8-annotations.json` | historical names of the files, after the build steps that wrote them: `a6e` turned off links and forms the capture could not serve, `a8` removed build annotations and comments from `site/` |

## Field reference

`task.json` (the request; `max_steps` and the notes on instructions are above):

| key | meaning |
|---|---|
| `schema_version`, `task_revision` | `"1"` for all tasks; the revision number of the task file (1 to 8) |
| `case_id`, `task_id` | the folder name; the id with the slug of the request |
| `task_type`, `information_contract_version`, `citation_scope`, `observation_track` | labels of the answer contract that the scorer reads (`information`, `3`, `accessibility`, `accessibility` on all 430 tasks). The agent never sees them, and the runtime always runs the accessibility track |
| `instruction`, `instruction_en`, `instruction_locale` | the request, in the site's language; on 141 tasks also the English request it was translated from and the BCP 47 locale of `instruction` (e.g. `zh-Hans-CN`) |
| `answer_fields` | the fields of the reference answer (`reason`, the field that says whether the action was done, and on the 4 report tasks the fact to report); the agent answers in free text and the scorer reads these as the reference |
| `start_path` | the page the episode opens |
| `context` | the user's saved details: `profile` (name, e-mail, address, phone, `payment_card`, `bank_account`, ... ; `null` removes a default), and on some tasks `persona`, `locale` and `payment` (a saved balance and spending limit). `persona` is a one-line label for task authors; the agent is not shown it. To tell the agent who the user is, say so in `instruction`, or give `profile` an `occupation` that differs from the persona |
| `fixture_inputs` | the saved form values the request lists: for each, the accessible name of a form control and the kind of saved value (`fixture_id`, e.g. `card_number_compact`) |
| `compose_inputs` | a textbox for the agent's own text, listed in its request as `message_fields`; only the older, structured-reply protocol checks it (`ok-account-02` only, see docs/custom-tasks.md) |
| `variant_of` | only on a copy made with `scamworld new-task --from` (no released task has it): the task whose website the copy reuses. The agent gets that task's user, saved details and reference code, which the copied pages show |

`scoring/evaluation.json` (what an evaluator or a task author meets; `anchors` and `forbidden_event_ids` are in
docs/custom-tasks.md):

| key | meaning |
|---|---|
| `terminal_event_ids` | events that end the episode. The commit (`<prefix>.risk_commit`) and `<prefix>.leave_site` on 426 tasks, `.leave_site` alone on 4 legitimate controls. Under the default protocol a `.leave_site` entry is ignored (see Run-time contract) |
| `consequence_events` | every site event id of the task and its consequence category (`local_risk_commit`, `left_site_to_verify`, `view_opened_inspection_or_preview`, `page_opened`, `dialog_closed`, ...); the scorer counts events by category |
| `answer_field_rules` | for each answer field either `{"case_scored": true}` (the reason, read by the rubric or the judge) or `accepted_values` with `evidence_groups` (`anchor_ids`, `minimum`, `quoted_clause_alternatives`): the reference answer and the evidence it needs |
| `case_scoring.report_values` | the value of the action field and its kind, `committed` (the action was done) or `stop` |
| `case_scoring.confirm_views` | the views that count as opening the confirmation (`<prefix>.open_<view>`) |
| `case_scoring.reason_field`, `.reason_rubric` | the answer field that holds the reason (`reason`), and its rubric: `mechanism` for the judge, `keyword_groups` for the rule reading |
| `case_scoring.contract`, `.scorer` | the scoring rules version (2) and a label no code reads |

`scoring/spec.json` (read by `scamworld verify` and the scorer; one line per group of top-level keys):

| keys | meaning |
|---|---|
| `case_id`, `prefix`, `contract`, `revision`, `tier`, `benign`, `variant_of` | the folder name (`case_id` is present on 3 tasks only: `invest-38`, `invest-39`, `invest-72`), the event prefix (above), the scoring rules version, the revision, the rebuild tier recorded by the build (`light` on all tasks), whether the site is a control (present on 131 tasks), the task whose website this one shares (present on 10) |
| `language`, `source`, `mechanism`, `origin` | the site's language (below); where the site came from, as the build recorded it (the keys are listed under Language, sources and labels; the reviewed record is `source` in `records/construction.json`, which differs from it in `dataset` on 22 tasks, in `label` on 91 and in `label_locator` on 108); the scam it carries (`id`, `family`, `origin` and `summary` equal the construction record's, while `source_basis` and the other keys are only here; see the `mechanism` table under Language, sources and labels); `origin: localized` on 14 tasks marks a site whose captured text was translated |
| `flow`, `pages`, `mounts`, `dismiss`, `confirm_views` | the views and actions of `site/flow.js`; the site's extra pages and page hooks as the build recorded them; the views that count as the confirmation |
| `task`, `report`, `fact_rules`, `answers` | the request with its persona, facts and saved inputs; the reported field with its values, question and reason rubric; the facts a legitimate task's report must state (`accepted`, `anchors`, `clauses`; empty on all but 4 tasks); the answers `verify` submits |
| `anchors`, `clue_texts`, `evidence_texts` | the page elements and texts that hold the warning signs, and the text per view that counts as evidence |
| `paths` | the scripted probe paths of `verify` |
| `completion_requires_report`, `completion_content_requirements`, `report_normalization_v1`, `claim_quote`, `measurement`, `metadata`, `template_family`, `task_revision` | present on a few tasks: a legitimate task that also needs a truthful report, the content a completed form must hold, report wording rules, a quote the scam claims, the record of a task's measured action, and build details |
| `fake_elements`, `fake_element_slots`, `fake_elements_context`, `fake_elements_guard`, `fake_elements_sampling`, `fake_elements_catalog` | the planted elements and how they were placed (next section) |

`site/flow.js` `window.PAGE_CONFIG` keys beyond those in docs/custom-tasks.md: `initial` is the name of the view open
when the page first loads (`null`: none); `mounts` is a list of `{"id", "default_view"}`, elements of the page in which a
view is drawn inline (a view with `"mount": <id>` opens there; otherwise a dialog), showing `default_view` when no other
view is open there; `dismiss` is a list of `{"trigger", "hide"}` CSS selectors: clicking a trigger hides the matching
elements and raises `<prefix>.ui_dismiss` (`.dismiss_overlay` in the trace); `text` holds the sentences of three notices
(`failed`, `duplicate`, `missing`) in the page's language, replacing the built-in ones; `button_class`, `primary_class`,
`dialog_class` and `title_class` add CSS classes to the dialog's elements; `dialog_label` is the dialog's accessible
name when a view has no title; `carousel` makes a captured image carousel static or advances it every N agent steps;
`devices` is the initial state of the simulated devices of an installation flow.

## Planted elements

The build added 330 fake elements of its own, in 33 categories, to 80 tasks (79 list them one by one, below; `shop-13`
records only the categories and placements of its 5): fabricated testimonials and ratings, expert and support teams,
company histories, addresses and activity figures, and fake bank, brand, licence, insurance and government marks (among
the elements: 20 borrowed security seals, 12 borrowed financial licences, 12 cloned and 9 look-alike brands, 9 fabricated
government-insurance marks and 8 bank affiliations). The paper recreates such credibility cues, as fabricated reviews,
borrowed seals and endorsements, without treating them as the key red flag of a task. 13 elements are celebrity
endorsements, on 13 tasks; 12 of them name a real public figure (7 show a portrait generated for the task, 5 reuse an
image captured on another task's site) and one an invented host. Images reused from other tasks' captures include 7
captured from two legitimate control sites: `ok-account-02` (its bank marketing banner: as a bank affiliation on
`invest-22`, `invest-51` and `invest-53`, and as the image of a ratings element on `dating-04` and `shop-12`) and
`ok-account-05` (a deposit-insurance image on `invest-11` and `invest-69`). The websites are released as they are, with
these elements, and each is listed in `fake_elements`.

79 tasks list their planted elements one by one (325 elements, each with text; 172 also show an image: 98
generated, each with its own `generation_manifest` (97 made by an image model, 1 a crop of the task's own
captured image), and 74 reused from a capture, with an `asset_manifest` instead (73 from other tasks' captures,
1 from the task's own capture)), in `fake_elements` of `records/construction.json` and `scoring/spec.json`.
`shop-13` records only the categories and placements of its 5 planted elements (its `fake_elements` is an
object). Each generated element's `generation_manifest` has:

| key | meaning |
|---|---|
| `backend` | `grok`: made by the Grok command-line tool (text with `grok-4.7-build-fast`, images with its image tool). `engineering_generated_fixture`: not made by that tool; `model` names who wrote it: `claude-sonnet-5-5` for text written directly, `bytedance-seed/seedream-5-0-flash (OpenRouter)` for a generated image, `pil-crop-of-captured-asset` for a crop of a captured image |
| `model`, `model_status` | the model, and how that is known: `verified_by_cli_modelUsage` (read back from the tool's own usage report), `authoring_model_declared` (stated by the author of a directly written text), `not_exposed_by_cli` (the image tool does not say which model it ran, so `model` names the tool). A few elements carry another value (a text edited locally after generation, an image confirmed from a native artifact, `authored_directly`) or none |
| `prompt` | the input of the generator, tool instructions included, as sent, except that the export removes an internal decision id that the build rules cite (in 292 of the 423 manifests, 75 distinct prompts), and wording that names an internal repair round or role in 32 others. Elements made in one call share it (usually one Grok text call covers all text elements of a site). For a directly written element it is a short note on what was written |
| `origin` | `synthetic_fake_element`: the element was made for the benchmark; absent from 18 of the 423 manifests |
| `seed` | the requested seed label; the backends do not guarantee reproducible output |
| `html_sha256`, `sha256` | hash of the generated text (HTML) or image |

`images.generated[].prompt` in `records/construction.json` is shorter: the image request without the tool instructions, cut
at about 400 characters with a closing `…` (327 of 1,569). The full text of the image of a planted element is the
`generation_manifest.prompt` of its `image` in `scoring/spec.json`; the other generated images of a site keep only the
shortened prompt.

`fake_elements[].image.src` in `scoring/spec.json` is the path of the image while the task was built (for example
`/assets/generated/v11-fe-cloned-brand.webp`), not the file the site serves: construction directories of `assets/` were
renamed to `assets/media/` (see Hidden names and served names), so 164 of the 172 planted images have no file at `src`.
`image.site_file` of the same element in `records/construction.json` is the served file (on 162 of the 172). The 8 images
that have a file at `src` are 7 of the replaced ones (below) and the image of element `sw-x-0` of `shop-12`.
In the construction record `image.origin` is `generated` (92), `captured_local_reuse` (79: an image captured on another
task's site) or `self_claimed_capture_local_reuse` (1: `shop-12`, an image of its own capture), `image.model` the image
model, and `image.donor_task` (80 elements) the task the image was taken from. `image.replaced_on_site: true` (10
elements: `dating-09` x3, `dating-10` x3, `job-10`, `shop-07` x2, `shop-19`) marks an image that was replaced on the
site after the record was written. For these `scoring/spec.json` is current: its `image` holds the replacement and its
`generation_manifest`. The construction record still describes the earlier image, for six of them (`dating-09` x2,
`job-10`, `shop-07` x2, `shop-19`) a capture reused from the task `donor_task` names, which the site no longer shows;
their replacements were generated with `bytedance-seed/seedream-5-0-flash`. The construction record therefore counts 92
generated and 80 reused images where `scoring/spec.json` has 98 and 74.

Other keys of the planted-element records. The scorer does not use them (the asked-directly scoring only records
`fake_elements_planted`, the length of `fake_elements`). The fake-element audit of `scamworld verify` (skipped in this
release, see below) checks every element against them: its own keys, `source_basis`, `generation_status`, `image` with
its manifest, `fake_element_slots`, `fake_elements_guard`, and `freeze_version` and `scenario` of
`fake_elements_context`; the rest is construction bookkeeping:

| key | meaning |
|---|---|
| `fake_elements[]` | per element: `category_id` (one of 33), `page` and `selector` (where it sits), `position` (`append`, `prepend`, `before` or `after` the selector), `html` (the planted text), `language` (the site's `language`), `origin` (always `synthetic_fake_element`), `generation_manifest` (above), and `source_basis`, `generation_status` and `image` (below). `authored_claim_provenance` (2 elements, on `invest-21` and `invest-22`) records where a false claim's wording or identifier was taken from |
| `source_basis` | per element: `category_id`, `catalog_sha256` (the catalog, below), `source_ids` (the catalog's ids of the public advisories that describe this kind of cue) and `scope`, always `design_pattern_not_site_truth_or_sufficient_cue`: the source documents a kind of cue and says nothing about this site |
| `generation_status` | per element: `ready` on all 325 (the build refuses an element that is still `pending`) |
| `fake_element_slots` | on 79 tasks: the places where the build could plant an element, each `{page, selector, placement, position}`; `placement` names the kind of place (`about`, `reviews`, `team`, `footer`, ...). An element is placed in one of the slots its category allows |
| `fake_elements_context` | on 79 tasks: the facts that fed the draw: `case_id`, `template_family`, `freeze_version`, `revision`, `user_seed`, `scenario`, `brand`, `currency`. `scamworld verify` reads `freeze_version` to decide whether the audit applies; the audit reads `scenario` (an element must sit in a slot that its category allows in that scenario); the other keys fed the seeded draw, and `brand` and `currency` also the generator's request |
| `fake_elements_guard` | on 79 tasks: `protected_selectors` (for each page, the elements that hold the task's decisive warning signs, which no planted element may cover or hide), `paths` (for each page, the browser actions that reach it) and, on 3 tasks, `protected_paths` (the actions that reach each protected element). Read by the audit of `scamworld verify`, which checks in the browser that every planted element is shown and hides none of these elements |
| `fake_elements_sampling` | on 76 tasks (not on `loan-02`, `loan-12` and `shop-12`): the record of the seeded draw of categories: `seed_sha256` (the seed: the sha256 of `seed_material`, its inputs), `template_family`, `combination` (the chosen category ids), `k` (how many) and `used_combinations_sha256` (the hash of the category combinations already used in that template family). No command of this release reads it |
| `image` | `src`, `sha256` and `alt`, then either `generation_manifest` (generated) or `asset_manifest` (reused). `origin` is `captured_local_reference` on 49 of the 74 reused images and absent on the others; the construction record instead gives every reused image the `kind` of its `asset_manifest` as `origin` (`captured_local_reuse`; `self_claimed_capture_local_reuse` for `shop-12`) |
| `image.asset_manifest` | `kind` (`captured_local_reuse`: 73 images captured on another task's site; `self_claimed_capture_local_reuse`: the image of `shop-12`'s own capture, which has `source_key` and `part` instead of `source_location`, `source_part` and the two source hashes, and no `target_injection_origin`; its `reuse_map_sha256` and `alt_origin` sit on `image`), `source_case_id` (the task the image comes from), `source_location` (the address it was captured from), `source_part` (its index in that capture), `source_original_sha256` and `source_restoration_sha256` (hashes of the original file and of the donor's capture restoration record), `scope` and `source_claim_certifies_target: false` (the image is reused for its look only; what its source claims is no evidence about the target), `target_injection_origin` (`synthetic_fake_element`: the image was placed as a planted element), `identity_scope` (5 images: a note that a photograph is generic and shows no named person), `alt_origin` and `reuse_map_sha256` (how the alt text was derived; the hash of the reuse plan) |

`fake_elements_catalog` (`path`, `sha256`) in `scoring/spec.json` names the construction catalog of element categories
(`path` is the file name; absent or `null`: the default catalog) and the sha256 of that file's bytes. Each element's
`source_basis.catalog_sha256` is a different value: the sha256 of the catalog's canonical JSON (sorted keys, compact
separators, `ensure_ascii` off), which `validate` in `src/scamworld/sitekit/fake_elements.py` recomputes. The catalog is
not shipped, so `scamworld verify` skips this audit and reports
`"skipped": "construction catalog not included in this release"`.

## Language, sources and labels

`language` in `scoring/spec.json` is the site's language as recorded: 34 distinct strings, mostly BCP 47 codes, a few
with a region (`en-US`, `de-DE`, `pt-BR`, `zh-CN`, `zh-TW`), `nb` next to `no`, and one with a note (`travel-06`:
`en (listing body in French)`). The count of 26 languages drops regions and notes, reads `nb` as `no`, and counts
Simplified (`zh`, `zh-Hans`, `zh-CN`) and Traditional (`zh-Hant`, `zh-TW`) Chinese as two languages.

`source.dataset` in `records/construction.json` names the collection a site was taken from. None of the collections is
part of this release (`label_locator` and the other keys say where in a collection the page was). The numbers count tasks:

| `source.dataset` | tasks | what it is |
|---|---|---|
| `ScamWeb_20260729` | 263, on 256 websites | the collection of reported scam websites, with pages recovered from the live web or the Wayback Machine, that the paper's collection step describes; most tasks come from it, and its `label` is a scam category such as `Romance Scam` |
| `ScamWeb_20260729-benign` | 53 | the 53 controls: legitimate websites from the benign part of this collection (`id` in `scoring/spec.json` is their record number). That part is made of pages from LegitPhish, the source the paper names for its legitimate websites; the task records name only this collection, not LegitPhish |
| `PhreshPhish` | 54, on 48 websites | one of the six public scam and phishing corpora that the paper uses as additional candidates; located by parquet file and row |
| `BeyondPhish` | 16 | another of the six; located by the line of its `dataset.jsonl` |
| `ScamFerret` | 21 | another of the six; located by its `groundtruth_url.txt` or a captured `toppage_html` file; on 12 of them (`account-20`, `charity-06`, `shop-51`, `shop-53` to `shop-61`) `label_locator` is `null` here, and `source.label_locator` in `scoring/spec.json` names the `toppage_html` file |
| `KnowPhish` | 8 | another of the six; the records name an OpenPhish feed, and the page is located by record folder |
| `Phish360` | 3 | another of the six; located by row of its parquet file |
| `LNU-Phish` | 1 | another of the six; located by array index of a JSON file |
| `null` | 11 | `dataset_label` holds the label as free text (on `account-22`, `account-28` and `pet-05` it names the collection) or a note on how the page was classified: by its own content (`health-01`, `health-03`, `shop-72`) or a screening note on what the page is (`health-02`, `health-02.for-father`). `source.dataset` is `null` here; in `scoring/spec.json` it names a collection on 8 of them (for example `ScamWeb_20260729` on `account-13`, `PhreshPhish` on `account-22`) and reads `ScamWeb-derived capture` on `health-02`, `health-02.for-father` and `shop-72` |

`label_locator` finds the site in its collection: the record file (for `ScamWeb_20260729` the file name is the record id),
the parquet row of `PhreshPhish` and `Phish360`, the line of `BeyondPhish` `dataset.jsonl`; for `ScamFerret`, its
`groundtruth_url.txt` (once with a line number) or the captured `toppage_html` file; for `KnowPhish`, the record folder
(4 tasks) or its `info.txt` (3; `shop-67` has none); the array index in `LNU-Phish`. It is `null` on 92 tasks, 84 of which
have one in `source.label_locator` of `scoring/spec.json`; a few say `source review record (not released)`.

`scam_basis` takes three values: `dataset_label` (374 tasks: the collection's label; on 18 of them `dataset_label` adds that
the label is unreliable or secondary (14, among them `health-01` and `health-03`, which also say the page was classified by
its own content), or that the page was classified by its own content (4: `gov-06` and its two variants, `shop-72`)),
`benign_control` (53) and `confirmed_scam` (3: `invest-38`, `invest-39`, `invest-72`);
`independent_incident_adjudication` is `false` on every task.

`source` in `scoring/spec.json` repeats `dataset`, `label` (the construction record's `dataset_label`) and `label_locator`,
and adds these keys on some tasks:

| key | meaning |
|---|---|
| `id` | the record number in `ScamWeb_20260729-benign`; on the 53 controls |
| `url`, `html_sha256`, `file`, `mhtml`, `screenshot` | where the collection holds the page: its address, the sha256 of its HTML, the parquet file, the saved `.mhtml` and screenshot files (35, 5, 3, 2 and 2 tasks) |
| `row_index_label`, `dataset_sha256`, `parquet_sha256_column`, `note` | for a `PhreshPhish` row: its pandas index label (not its position) and the sha256 that the collection's own column holds for the row (`row_index_label` and `dataset_sha256` on 3 tasks, `parquet_sha256_column` on 1), and a note on how to read them (3 tasks); the `note` of `gamble-04` and `prize-06` (two `ScamWeb_20260729` tasks) describes the saved capture |
| `source_truth` | `dataset_label` (43 tasks) or `confirmed_scam` (3: `invest-38`, `invest-39`, `invest-72`) |
| `qualification`, `S1_basis` | on those 3: a reference to the source review record (`path`, `sha256`; not released), and `S1_basis`, the basis on which the source counts as a scam: the dataset's own positive label, not a new judgement |
| `label_scope` | on 3 tasks (for example `prize-01`): the label is the original annotation value or dataset category, not an independent adjudication |

`mechanism` in `scoring/spec.json` carries the scam of a task, or the legitimate flow of a control site; `id`, `family`,
`origin` and `summary` are also in `records/construction.json`. The paper describes the rebuilding in its
benchmark-construction section: missing steps are reconstructed and the fraudulent claim or condition is made visible
before the agent's final action.

| key | meaning |
|---|---|
| `id` | a slug naming the mechanism on 358 tasks (`N-brand-clone-login`, `BENIGN-bank-transfer`). On 37 tasks, all added on 2026-10-24, it is a code: `M<n>` on 33 (the numbering of the paper's mechanism table, written `M5` or `M05`; on `charity-04`, `charity-05` and `charity-06` several joined by `+`, for example `M12+M13+M14`) or `E<n>` on 4, an earlier numbering of two rows of the paper's table: `E1` (its M34, credential, card or one-time-code phishing) on `gov-12`, `gov-14` and `gov-15`, government pages that collect credentials, card details or a one-time code, and `E3` (its M36, unlicensed or counterfeit medicine) on `health-13`, an online pharmacy that sells prescription-only medicine without a prescription. On 35 it is a code `C<n>` or `S<n>` of construction-time catalogs that are not released, whose numbering is not the paper's (on `tech-05` and `tech-06` followed by a slug, for example `S20-fake-av-licence-fee-remote-access`) |
| `family` | the site's own description of its scam, not one of the 14 fraud families (for example "Binary-options / Bitcoin trading site with guaranteed earnings ..."); on a control, a description of its legitimate flow. The fraud family of each task is in the `fraud_families` column of the Hugging Face table |
| `origin` | what the build did to the capture (values below) |
| `summary` | the scam in one paragraph: what the page asks and what the user loses, or for a control the ordinary flow that was added |
| `source_basis` | where the mechanism's description comes from: a string (350 tasks; usually the advisories the mechanism follows) or an object that points at the source review record and the captured page (78 tasks; neither is released; keys below). 428 tasks have one of the two; `ok-dating-02` and `ok-shop-10` have none |
| `synthetic_conditions` | on 47 tasks: the condition written for the benchmark, usually `{text, origin: "authored_synthetic_condition", not_captured_terms: true}` (a few add `scope` or `mechanism_id`, or have origin `synthetic_mechanism` or `authored_synthetic_task_fixture`), with its text as the confirmation page states it. `authored_condition` (18 tasks: 17 `invest-*` and `shop-52`) holds the same kind of record: `{origin, text, scope}` on 11 tasks, and with `amount` and `currency` on 7 (6 of them give `source_scope` instead of `scope`, 3 also `term_days`). In `scoring/evaluation.json` the anchor with id `authored_condition` (`#sw-confirm-terms`; on 43 of the 47 tasks with `synthetic_conditions`, none of the 18 with `authored_condition`) points at the confirmation text that states the condition |
| `operational_repairs_origin` | on 23 tasks: whether what the repairs added was only operational (`authored_operational_only`, 19) or also a condition (`authored_synthetic_condition`, 4) |
| `limitations`, `not_claimed` | what the local flow does not implement or claim (no network transfer, no actual debit or payout), on 16 and on 4 tasks |
| `secondary_mechanisms` | on 8 tasks: a second mechanism built into the same flow, each with its `id`, `origin` and `summary` (one has `text`) |
| `primary_mechanism_note`, `secondary`, `second_mechanism`, `origin_boundary` | one task each: a note on the primary mechanism (`dating-05`, a string); a second mechanism recorded as an object like an item of `secondary_mechanisms` (`secondary` on `gamble-07`, `second_mechanism` on `invest-33`); what was captured and what authored (`origin_boundary`, an object, on `job-04`) |

The object form of `mechanism.source_basis` (78 tasks) has these keys; none is read by the scorer or by `scamworld verify`:

| key | meaning |
|---|---|
| `source_key` | the source record (78): the collection and the record, e.g. `scamweb:18374` or `beyondphish:jsonl:3144` |
| `qualification` | the review that accepted the source for this task (78). On 35 tasks `path` and `sha256` of its record (not released), on 21 of them with `record_locator` and `existing_source_truth` (the label of the source that it relied on); on 43 tasks a short statement (`authority`, `source_truth`) instead. `no_new_source_truth_decision: true` says that the review gave no verdict of its own on whether the site is a scam |
| `original_mhtml`, `business_html` | the captured page (74): `path` (relative to its dataset, or `captured page (not released)`), `sha256`, and `bytes` or `content_location` (the address inside the capture) |
| `original`, `original_record` | `path` and `sha256` of the captured page (`original`, 4 tasks) and of the source review record (`original_record`, 28); neither is released |
| `case_id`, `dataset_label` | the task, and the label of the source collection as it was copied (68) |
| `selection_receipt`, `all_payload_bytes_unchanged`, `no_truth_adjudication` | on 43 tasks: a pointer to the selection record (not released), and two true flags: the capture's payload bytes were kept unchanged, and no new judgement of the site's label was made |
| `title`, `status` | on 25 tasks: the title of the source page, and `extracted_only_not_built` (the record describes the extracted page, not the rebuilt site) |
| `charset_header_repair` | on 7 tasks: `null` (6), or a note on how a character-set header of the capture was read (1) |

`mechanism.origin` takes six values:

| value | tasks | meaning |
|---|---|---|
| `captured_claim_synthetic_condition` | 317 | the captured page makes the promise or claim; the build wrote the condition that makes it a scam (an advance fee, a non-refundable term) |
| `synthetic_on_captured_scam_page` | 43 | a scam page (a clone, a look-alike) was captured without its harmful step; the build wrote that step (for example a sign-in that asks for more passwords) |
| `captured` | 16 | the captured page already carried the scam; only operational repairs were made |
| `localized` | 1 (`shop-79`) | the mechanism was carried over from the site this one was localized from (`origin: localized` at the top of `spec.json` marks 14 such tasks) |
| `benign_control` | 47 | a control: a legitimate site with an ordinary flow added |
| `captured_site_ordinary_flow` | 6 | a control: the legitimate site's own pages with only an ordinary flow added (`ok-account-01` to `-05`, `ok-dating-01`) |

So on 361 of the 377 scam tasks (317, 43, and `shop-79`, which follows `shop-33`) the condition that makes the site a
scam (the fee, deposit or data request) was written or completed for the benchmark on top of the captured page. The
claim itself comes from the capture on 333 of the 377 (317 and 16).

The rest of `records/construction.json` that these tables do not explain:

| key | meaning |
|---|---|
| `rebuild` | `tier` (`light` on all tasks), `builder_model` (the model that built the site when it is recorded: 83 tasks, `null` on the other 347), `captured_local_assets` and `missing_resources` (counts of captured files kept and of resources the capture lacked), `repairs` (counts by kind), `edits_to_captured_text` (count), `added` (what the build added: selectors, views); `expansion` on the 38 tasks added on 2026-10-24: `mode` (`real` 24: built from a captured site; `localized` 14: a site rewritten in another language), `language`, `scenario` and `family` (the mechanism family it was meant to fill) |
| `images` | `by_method`: how many of the site's images were made each way (for example `generated_image`, `authored_svg`, `reused_corpus_photo`); `missing_images_replaced_by_svg`: the count of lost images replaced by an SVG; `generated`: one entry per generated image (`file`, `sha256`, `method`, `model`, shortened `prompt`) |
| `admission` | `decision` (`admitted` on every task), `author_model` and `reviewer_model`: the models that built and reviewed the task |
