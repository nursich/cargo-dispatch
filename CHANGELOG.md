# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-05

### Added
- Domain models for carriers, cargo requests and assignments with input validation.
- Haversine distances and vectorised distance matrices.
- Multi-criteria scoring (cost, reliability, rating) with configurable weights and
  priority multipliers.
- Greedy and optimal (Hungarian algorithm) allocation strategies.
- CSV input/output, allocation map, `cargo-dispatch` command-line interface.
- Sample data set for 18 cities of Kazakhstan and a reproducible benchmark script.
- Pytest suite with a 90 % coverage gate, Ruff and mypy checks.
- GitHub Actions CI (multi-OS, multi-Python), release workflow and Dependabot.
