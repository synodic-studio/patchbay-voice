fastlane documentation
----

# Installation

Make sure you have the latest version of the Xcode command line tools installed:

```sh
xcode-select --install
```

For _fastlane_ installation instructions, see [Installing _fastlane_](https://docs.fastlane.tools/#installing-fastlane)

# Available Actions

## iOS

### ios upload

```sh
[bundle exec] fastlane ios upload
```

Upload the already-built IPA to TestFlight (skips build)

### ios beta

```sh
[bundle exec] fastlane ios beta
```

Build and upload a new beta to TestFlight

### ios push_metadata

```sh
[bundle exec] fastlane ios push_metadata
```

Stage App Store metadata + screenshots on the editable version (no binary, no submit)

### ios push_screenshots

```sh
[bundle exec] fastlane ios push_screenshots
```

Stage App Store screenshots only (no binary, no metadata, no submit)

### ios bump_build

```sh
[bundle exec] fastlane ios bump_build
```

Increment CURRENT_PROJECT_VERSION in Project.swift, anchored to latest TestFlight build

----

This README.md is auto-generated and will be re-generated every time [_fastlane_](https://fastlane.tools) is run.

More information about _fastlane_ can be found on [fastlane.tools](https://fastlane.tools).

The documentation of _fastlane_ can be found on [docs.fastlane.tools](https://docs.fastlane.tools).
