# ScamWorld

**ScamWorld** is an interactive environment for evaluating web agents against online fraud. It reconstructs 363 reported scam websites, spanning 16 fraud scenarios, 38 fraud mechanisms and 26 languages, together with 53 legitimate control websites. All websites are served locally and run in a standard browser. Agents can observe screenshots, HTML or the accessibility tree, and act through clicks, typing, scrolling and navigation.

> **Coming soon.** We will release the environment as a Docker image, together with guides on how to
> define your own tasks on the websites, run your own agent, connect your agent's model API and write your own evaluation functions.

Paper: *ScamWorld: An Interactive Environment for Evaluating Web Agents Against Online Fraud* (arXiv link coming soon).

## Overview

<p align="center"><img src="assets/overview.jpg" width="100%" alt="ScamWorld overview: 16 fraud scenarios, 38 fraud mechanisms, example websites and the observation and action interfaces"></p>

## Example tasks

Each task pairs an ordinary user request with an interactive website. On a scam website, an observable red flag appears before the agent's final action, such as a payment, a credential submission or a software install.

<p align="center"><img src="assets/tasks.jpg" width="100%" alt="Task examples: user requests and browser states from three scam websites and one legitimate control"></p>

## How the websites are built

We collect scam URLs reported by victims, watchdogs and authorities, recover their pages from the live web or the Wayback Machine, annotate them against a catalogue of fraud mechanisms, and rebuild the selected websites so that each task can be completed in a browser.

<p align="center"><img src="assets/pipeline.jpg" width="100%" alt="ScamWorld construction pipeline"></p>

## Website gallery

<p align="center"><img src="assets/gallery.jpg" width="100%" alt="Start pages of 49 ScamWorld websites across fraud scenarios and languages"></p>
