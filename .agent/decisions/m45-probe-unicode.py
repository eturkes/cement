"""Cross-version stdlib semantics; no project imports or generated code."""
import json
import sys
import unicodedata

boundaries = "a\nb\rc\r\nd\ve\ff\x1cg\x1dh\x1ei\x85j k l"
whitespace = [f"U+{i:04X}" for i in range(0x110000) if chr(i).isspace()]
strip_cases = [" X ", "​X​", "﻿X﻿", "\x1cX\x1c"]
normalization_cases = ["é", "Ａ：Ｂ", "①", "Straße", "Ᲊ", "\U0001e030"]
print(json.dumps({
    "python": sys.version.split()[0],
    "unicode": unicodedata.unidata_version,
    "splitlines": boundaries.splitlines(),
    "splitLF": boundaries.split("\n"),
    "whitespace": whitespace,
    "strip": [[s, s.strip()] for s in strip_cases],
    "normalization": {
        s: {
            "NFC": unicodedata.normalize("NFC", s),
            "NFKC": unicodedata.normalize("NFKC", s),
            "lower": s.lower(),
            "casefold": s.casefold(),
        }
        for s in normalization_cases
    },
}, ensure_ascii=True, sort_keys=True))
