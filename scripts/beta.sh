#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../ios"
exec mise exec -- bundle exec fastlane beta
