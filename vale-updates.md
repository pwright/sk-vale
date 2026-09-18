# Updating Vale

Three things to keep in sync: the Vale binary (local + CI), and the AsciiDocDITA style package.

## 1. Local Vale binary

Installed via Homebrew:

```bash
brew upgrade vale
vale --version
```

Check the latest release at https://github.com/errata-ai/vale/releases.

## 2. GitHub Actions workflows

Both workflows pin a `VALE_VERSION` variable that downloads a specific binary:

- `.github/workflows/skupper-vale.yml`
- `.github/workflows/apicurio-vale.yml`

Update the version in each file:

```yaml
VALE_VERSION=3.22.0  # change this to the latest
```

## 3. AsciiDocDITA style package

Defined in `.vale.ini` under `Packages`. The URL points to the `latest` release of `jhradilek/asciidoctor-dita-vale`, so running sync always pulls the newest version:

```bash
vale sync
```

Check what changed:

```bash
git diff .vale/styles/AsciiDocDITA/
```

Check the latest release at https://github.com/jhradilek/asciidoctor-dita-vale/releases.
