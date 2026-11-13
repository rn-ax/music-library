---
type: Functionality
title: Delivery
description: How changes reach TrueNAS: CI checks, automatic merge, image publishing, deploy, the snapshot taken before each deploy, and rollback.
tags: [delivery, ci, deploy, merge, rollback, backup, snapshot, ghcr, truenas, image, compose]
---

# Context

No human reviews code or pull requests. The acceptance criteria and CI are what make a change safe, and agents implement, test, merge, deploy and roll back.

The repository is private on GitHub's Free plan, which has no branch protection, so the merge gate is workflow logic that a direct push could bypass.

CI runs on the self-hosted `contabo` runners, which can reach TrueNAS. A deploy sends `compose.yaml` to TrueNAS through its API using a key of its own stored as a repository secret. The image is published as `latest` and under a CalVer version, and a deploy pulls it before redeploying.

The backup before a deploy is a ZFS snapshot of the datasets the stack uses. Rolling back discards what was written after the deploy, which suits a single-user stack.

# Criteria

- AC-31: A pull request is squash-merged automatically when its CI run passes.
- AC-32: CI runs every acceptance check on each push to a branch and on `main`.
- AC-33: A push to `main` publishes the image to ghcr as `latest` and as `YYYY.MM.DD.<run number>`.
- AC-34: A merge to `main` updates the TrueNAS app to the new image and applies `compose.yaml`.
- AC-35: Before each deploy, snapshots named `deploy-<version>` exist of `Storage/Configuration/music-library` and of `Storage/Music`.
- AC-36: A deploy after which not all services are running five minutes after the redeploy is rolled back by redeploying the previous image version and restoring those snapshots.
- AC-37: A rolled-back deploy marks its CI run as failed.
