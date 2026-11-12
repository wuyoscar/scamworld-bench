# The task folder

```
my-task/
  task.json                 the request (public to the agent)
  site/index.html           the website; more pages and assets may sit next to it
  site/flow.js              dialogs, the risky action and its receipt (window.PAGE_CONFIG)
  site/pagekit.js           page runtime, copied from the package: do not edit
  scoring/evaluation.json   hidden: forbidden event, evidence anchors, reason rubric
  scoring/spec.json         hidden: scripted probe paths and reference answers (read by verify)
  source/provenance.json    the address the browser shows for the site
  records/                  only in copies of released tasks; leave it
```

The agent reaches only what `site/` serves, under the address in `source/provenance.json`. Every other host is blocked.

## Which file changes what

| to change | edit |
|---|---|
| what the user asks for | `task.json` `instruction` (and `instruction_en` if present) |
| who the user is, their saved details | `task.json` `context.profile` (`null` removes a field); pages that show the user must change too |
| a page's content | `site/*.html` |
| a dialog, the risky action | `site/flow.js` |
| what counts as the risky action, the warning-sign text, the reason rubric | `scoring/evaluation.json` |
| the scripted paths and reference answers `verify` replays | `scoring/spec.json` |
| the address shown in the browser | `source/provenance.json` `source.url` |

## A new website, in order

`scamworld new-task <folder> --url https://<made-up-plausible-domain>/` writes a small parcel-fee website that runs as it
is (`--benign` writes its legitimate control). Change it in this order, and run `verify` after each step:

1. `site/index.html`, and more pages next to it. Keep the two `<script>` lines at the end of every page.
2. `site/flow.js`: the dialogs and the risky action.
3. `scoring/evaluation.json`: `anchors` (the warning signs: an id, a selector, the phrase) and `reason_rubric`.
4. `scoring/spec.json`: `clue_texts`, `paths` (the scripted routes `verify` replays) and `answers`.
5. `task.json`: `instruction`.

Then read one real run, and `scamworld signs <folder>` to see that each warning sign is reached. The longer walk-through
is docs/custom-tasks.md section C.

## Changing the request

A new `instruction` leaves `verify` passing. If the new request changes what the right outcome is (for example the user only asks for a price), either keep the scoring files and score with your own evaluator, or change `scoring/evaluation.json` and the `answers` of `scoring/spec.json` (docs/custom-tasks.md section C).

## Page markup

Interactive steps go through `pagekit.js`. Load `flow.js` and then `pagekit.js` at the end of every page:

```html
<button type="button" id="pay" data-dx-do="open:confirm">Pay USD 1.95</button>
<script src="/flow.js"></script>
<script src="/pagekit.js"></script>
```

| `data-dx-do` | effect |
|---|---|
| `open:<view>` | opens a dialog view of `flow.js` |
| `close`, `back`, `cancel` | closes it / one view back / cancels |
| `act:<action>` | runs a risky action of `flow.js` (a payment, a credential, an install) and records `<prefix>.risk_commit` |
| `choose:<key>=<value>` | records a choice |
| `go:<page>` | navigates to a page listed in `flow.js` `pages` |
| `leave:<target>` | a link that leaves the site; recorded as `<prefix>.leave_site` |

Inputs need an `id` and an accessible name (`aria-label` or `<label>`), so that the agent sees them. Asset paths are absolute (`/assets/logo.png`).

## `verify`

`scamworld verify <folder>` replays the paths of `scoring/spec.json` in a real browser: find the warning sign and stop, open the confirmation and cancel, commit, report a commit that did not happen. It checks that each is scored as intended. The last line is `PASS` or `FAIL`; the lines above are one probe each with `"ok": true/false`. Run it after every change to the site or the scoring files.

In `spec.json`, `clue` must show the warning sign and `commit` must end with the risky action; `answers.stop` names the sign, `answers.stop_vague` does not.

## Good tasks

The warning sign is on the website before the risky action (start page, terms, confirmation dialog), so a careful agent can find it by browsing. A sign that is only in the address is weak evidence. The event prefix of your own task must not start with `ev`.
