# Remaining ContentType warnings

## Problem

After fixing missing content-type markers in the input markdown, 6 files still trigger `AsciiDocDITA.ContentType` warnings. These are all stub files created by `leben.py` during the split step — they contain only an ID and title with no body content, so the parent section's `:_mod-docs-content-type:` attribute never reaches them.

Affected files:

- `assemblies/assembly-kube-yaml-index.adoc`
- `modules/console-index.adoc`
- `modules/kube-yaml-service-exposure.adoc`
- `modules/kube-yaml-site-configuration.adoc`
- `modules/system-yaml-index.adoc`
- `modules/troubleshooting-index.adoc`

### How it happens

When a source file like `kube-yaml/site-configuration.md` has this structure:

```
<a id="kube-creating-site-yaml"></a>
# Creating a site on Kubernetes using YAML
<!--ASSEMBLY-->

Some intro text...

<a id="kube-creating-simple-site-yaml"></a>
## Creating a simple site on Kubernetes using YAML
<!--PROCEDURE-->
...
```

`merge.py` converts `<!--ASSEMBLY-->` into `:_mod-docs-content-type: ASSEMBLY` and attaches it to the body after the `# H1` heading.

`leben.py` then splits on each `[id="..."]` boundary. The first ID becomes a parent stub (`kube-yaml-site-configuration.adoc`) containing only the ID and title — the `:_mod-docs-content-type:` attribute that follows in the body gets assigned to the next module instead.

The same pattern applies to index-style files (`console/index.md`, `troubleshooting/index.md`, `system-yaml/index.md`) where the H1 heading and its `<!--ASSEMBLY-->` or `<!--REFERENCE-->` marker produce a stub that loses the attribute.

## Proposed solution

Modify `leben.py` (`ModuleFactory.write`) to detect when a file has no `:_mod-docs-content-type:` attribute in its body and inject one based on context:

- Assembly files (`is_assembly=True`): inject `:_mod-docs-content-type: ASSEMBLY`
- Module stubs with no body content: inherit the content type from the first attribute line found in the original section body before it was split away

This keeps the fix local to the split step without requiring changes to the input markdown or `merge.py`.
