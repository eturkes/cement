# Projection programs

A projection maps a raw input to its case key. Use one only when the operation is projectable:
every output is a procedure that reads values from the input, and no output contains a value
copied from an input. Then documents that share one layout need one procedure, and the
projection lets one case cover every document of that layout. Cement verifies the program
against every confirmed raw input. An input that the program does not recognize goes to the
model.

## Program format (`cement-projection-v1`)

`cement-projection-v2` has the same format; its labels end at `:` or the full-width `：` (U+FF1A).
The drafted program is v2 only when an input labels with `：`; a v2 label or section literal holds
neither colon.

```json
{"abi": "cement-projection-v1",
 "text": "document",
 "keep": [],
 "layouts": [
   {"name": "progress note",
    "title": "PHYSICIAN PROGRESS NOTE",
    "entries": [{"label": "Patient"}, {"label": "MRN"}, {"label": "Date"},
                {"label": "Provider"}, {"section": "Subjective"}, {"section": "Objective"},
                {"section": "Assessment"}, {"section": "Plan"}]}]}
```

- `text` names the input field that holds the document text. The input object must have
  exactly the field that `text` names plus the fields that `keep` lists, and nothing else.
- `keep` lists other input fields (sorted, unique) whose values become part of the key, for
  example a field that selects which fields to extract. Values in `keep` stay exact.
- `layouts` lists the layouts that you saw in raw inputs. `name` is for display only. `title` is
  the document's first line. `entries` is the ordered structure: `{"label": "K"}` for a line
  `K: value`, and `{"section": "H"}` for a heading line `H:` followed by body lines.
- Literals must not contain control characters or a leading or trailing space or tab. Label
  and section literals must not contain `:`. Two layouts with the same title and entries are
  invalid.

## How Cement reads a document

1. Line endings become LF. Trailing spaces and tabs are removed from each line. Leading and
   trailing blank lines are removed, and runs of blank lines become one.
2. Blank lines split the text into blocks. The first block is the title line and its label
   lines. A later block is a section (a heading line `H:` and at least one body line without
   `:`) or a block of label lines.
3. A label line splits at its first `:`. The part before it, trimmed, is the label. The rest is
   the value, and the value never enters the key.
4. The structure must equal one layout exactly, in order. An extra label, a missing line, a
   different title or a changed letter means no match.

The key is the title, the structure and the `keep` values. Values from the text never enter the
key, so a new document of a known layout reaches its case even when every value is new.

## Writing a program

1. Derive the program: `cement learn cases "$OP" --projectable` writes one layout for each
   distinct title and structure in the raw inputs of the pending proposals and the active
   examples, and prints it as `program`. `cement learn merge --projectable` groups by the same
   program, and `cement learn publish --projectable` sets the program derived from the confirmed
   inputs. Each command derives it again, so nothing needs a saved copy.
2. Write nothing for an input whose text has no form layout: the command leaves it with the model.
3. Check `unprojected` in the work list: an input there has a layout that the program does not
   list, and it stays with the model.
4. To extend the program by hand, save the derived `program` as `program.json`, copy each title
   and label exactly, including case, and follow the manual route (`workflow.md`). Group by the
   candidate before you review anything, and test it before you set it:

   ```sh
   cement learn cases "$OP" --program - < program.json
   cement projection test "$OP" --program - < program.json
   cement projection set "$OP" --program - --actor learning-pass < program.json
   ```

`projection set` refuses, and writes nothing, when the program is invalid, when a layout has no
active example, when one key groups examples with different outputs, or when no active example
matches. Setting a program retires the drafts and verified builds of another program. Promoted
versions keep their own program.

In the report, state the assumption that the projection makes: documents with one layout need
one procedure.
