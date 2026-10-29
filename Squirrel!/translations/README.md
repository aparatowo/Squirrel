# Translations

Every text Squirrel! shows is written in English in the code; these files give it in other languages. One file per
language: `pl.tsv` (Polski), `fr.tsv` (Français), `de.tsv` (Deutsch).

## The format

A plain text file (UTF-8), easy to edit in any editor or spreadsheet:

```
en	pl
Settings	Ustawienia
Synced %d of %d	Zsynchronizowano %d z %d
```

- The first line names the columns: `en`, a tab, the language code.
- Then one text per line: **the English text, a tab, the translation**. Do not change the English column - it is how
  the text is found.
- `\n` is a line break inside a text (the help of a setting), `\t` a tab.
- `%d`, `%s`, `%02d` ... are filled in by the app: keep the same ones, in the same order.
- An empty translation is shown in English.
- Keep it short: a setting's name has at most 18 characters, a line of help 38 (`check.py` says when one
  is longer), a line of the Cardputer's screen 38-40.

## English

The English texts are the code's own. `en.tsv` holds only the few that the English screens show differently - a word
play the code need not carry (*Notifications* → *Nutifications*: a squirrel's notifications). It is built like the
others; any text it does not list stays as the code has it.

## Improving a translation

Change the text after the tab, then (from the folder `Squirrel!/`):

```bash
python3 tools/i18n/check.py      # placeholders, lengths, what is missing
python3 tools/i18n/build.py      # writes lang/<code>.py, which goes into the firmware
```

and build the firmware as usual. Please send your changes back (a pull request), so everyone gets them.

## A new language

Copy one of the files to `<code>.tsv` (e.g. `es.tsv`), change the first line to `en<TAB>es`, translate the second
column, and add the code to `LANGUAGES` in `i18n.py` and to the choices of `LANGUAGE` in `appconfig_schema.py`. Its
name under *Language* goes to `_NATIVE_NAMES` in `screens/personalize_screen.py`. Letters the watch's font does not
have yet are shown plain; `tools/fonts/make_latin_glyphs.py` adds them.

## Your own texts on the device - no new firmware

Put a file `lang_<code>.tsv` in Squirrel!'s folder on the device (`/Squirrel` on the Cardputer's SD card, `/Squirrel`
on the watch), in the same format, with only the lines you want different:

```
en	pl
Mind dump	Głowa pełna myśli
```

It wins over the built-in translation; `lang_en.tsv` changes the English texts. Read when the language is chosen (or at
start-up). Only these lines are kept in memory.

How it works inside: [docs/implementation/en/i18n.md](../../docs/implementation/en/i18n.md).
