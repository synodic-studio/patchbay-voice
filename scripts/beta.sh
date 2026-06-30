#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec mise exec -- bundle exec fastlane beta
