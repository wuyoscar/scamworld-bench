# Disclaimer and licences

## What the websites are

The websites in `tasks/*/site/` (and in the Docker image) are **research reconstructions of scam pages that were reported
by victims, watchdogs or authorities and are no longer online**. They were rebuilt so that web agents can be tested against
online fraud in a closed, local environment. The condition that makes a site a scam (the fee, deposit or data request) was
written or completed for the benchmark on 361 of the 377 scam tasks (`mechanism.origin` in `scoring/spec.json`:
`captured_claim_synthetic_condition` on 317, `synthetic_on_captured_scam_page` on 43, and `shop-79`, localized from
`shop-33`); the claim itself comes from the capture on 333 of the 377 (those 317 and the 16 `captured`). On the 14
tasks whose site was localized into another language (`origin: localized` at the top of `scoring/spec.json`) the
captured text was translated.

- **Brands, organisations and people of the captured scams.** Many scam pages imitate real companies, banks, government
  agencies, charities or public figures, and some use the likeness or name of a real person, as the original scam did.
  Their presence implies no affiliation with, endorsement by, or claim about the brand, organisation or person. All
  trademarks belong to their owners.
- **Elements planted by the build.** On 80 scam tasks the build added 330 fake elements of its own (33 categories, among
  them fabricated endorsements, reviews, credentials and company histories, and bank, brand, licence and government
  marks). They include 13 celebrity endorsements, 12 of which name real public figures, 7 with AI-generated portraits
  (on `shop-01` of a fictional woman, not of the person named) and 5 with an image reused from a capture, and 172 images
  in all: 97 made by an image model, 73 reused from other tasks' captures (7 of them from legitimate control sites), 1
  reused from the task's own capture and 1 cropped from the task's own captured image. The endorsements, reviews,
  credentials and marks are fabricated for the benchmark; the reused images are real captures shown in a context the
  benchmark invented. None implies affiliation with, endorsement by, or a statement by the people and organisations
  named, and the quotations and credentials shown were never given by them. The elements are listed per task in
  `scoring/spec.json` (`fake_elements`).
- **Users and contact details.** The users in the tasks (the signed-in user and the saved details: names, e-mail, phone,
  address, cards) are fictional. Scam websites keep the contact details the scammers published on the original pages, as
  part of the reconstructed fraud; some placeholder contacts were replaced with fictional ones. Legitimate control
  websites keep the organisations' public contact addresses; personal addresses were removed. Do not contact any address
  in the dataset or send it money. The sites send nothing anywhere, and forms, payments and downloads raise local events
  only; the agent's prompt carries the task profile to the model API you run.
- **The legitimate control websites** are reconstructions as well, used to measure over-refusal; they are not the
  organisations' real sites.

## Use

For research and evaluation of AI agents and of anti-fraud methods only.

- **Do not deploy the websites on the public internet**, do not make them reachable by people who might mistake them for the
  real thing, and do not use them, or any part of them, for phishing, fraud, impersonation or any other harmful purpose.
- The runtime serves each site on `127.0.0.1` only and blocks every request to other hosts unless
  `SCAMWORLD_OFFSITE=allowlist` is set; leave that option off unless you need it.
- If you are a rights holder and want a page removed from the release, open an issue in this repository.

## Licences

- **Code** (`src/`, `examples/`, `deploy/`, `tests/`, `docs/`, `configs/`): Apache License 2.0 (`LICENSE`). The vendored
  AgentLab and BrowserGym experiments code in `vendor/` keeps its own Apache 2.0 licence (copyright ServiceNow).
- **Website and task data** (`tasks/`, the task files in the Docker image): Creative Commons Attribution-NonCommercial 4.0
  International (CC BY-NC 4.0, `LICENSE-DATA`), subject to the use restrictions above. The licence covers the
  reconstruction work only; it grants no rights in any third-party trademark, logo, name or likeness in the pages, whether
  captured from the original scam or planted by the build, including the AI-generated portraits of real people. Their
  appearance implies no endorsement or affiliation.

The data is provided "as is", without warranty of any kind. The authors are not responsible for any use of the data or
code that violates these terms or applicable law.
