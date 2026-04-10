I want to update merged.adoc so that running the following pipeline does not produce errors or warnings


Also check under each heading the following attribute should be set once:

:_mod-docs-content-type:

The possible values are:

1. For headings with child or sub headings

:_mod-docs-content-type: ASSEMBLY 

2. For headings with gerunds (eg configuring)

:_mod-docs-content-type: PROCEDURE

3. For all other headings

:_mod-docs-content-type: REFERENCE

```
 ./leben.py merged.adoc ; vale assemblies/ modules/  
```

