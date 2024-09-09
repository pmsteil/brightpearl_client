# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New initialization parameters: `api_base_url`, `brightpearl_app_ref`, and `brightpearl_account_token`
- Optional initialization parameters: `timeout`, `max_retries`, and `rate_limit`
- Input validation for client configuration using Pydantic
- Rate limiting mechanism to respect API rate limits
- More comprehensive error handling with custom `BrightPearlApiError` exception
- Detailed logging throughout the client for better debugging
- New unit tests for client initialization and error handling

### Changed
- Updated client initialization to use separate parameters instead of `api_url` and `api_headers`
- Renamed `parse_order_results` to `_parse_api_results` and made it an internal method
- Updated `get_orders_by_status` to include `parse_api_results` parameter
- Improved docstrings and type hints throughout the codebase
- Updated README with new usage examples and parameter descriptions
- Refactored unit tests to accommodate new client structure and features

### Removed
- Removed `api_url` and `api_headers` parameters from client initialization

### Fixed

### Security

## [0.1.0] - 2023-05-24
- Initial release

[Unreleased]: https://github.com/pmsteil/brightpearl_client/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pmsteil/brightpearl_client/releases/tag/v0.1.0
