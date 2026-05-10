# Push to GitHub

This bundle is a self-contained git repository with one prepared commit.
Three ways to publish it. Pick whichever fits your tooling.

## Option A — `push-to-github.sh` (the easiest path)

If you have the `gh` CLI installed (https://cli.github.com) and are
authenticated:

```bash
unzip paper3.zip
cd paper3
chmod +x push-to-github.sh
./push-to-github.sh paper3-aad-harness --private
```

The script will:
1. Verify you're inside the unpacked bundle.
2. Verify `git` and `gh` are installed and authenticated.
3. Create the GitHub repo (`paper3-aad-harness` by default, private by
   default), set `origin`, and push the prepared commit.

That's it. The script prints the new repo URL when it's done.

To customize: `./push-to-github.sh <repo-name> --public` (or
`--private`, the default).

## Option B — Manual `git push`

If you prefer not to use `gh`:

```bash
unzip paper3.zip
cd paper3

# 1. On github.com: click "+ → New repository". Name it (e.g.
#    "paper3-aad-harness"), set visibility, DO NOT initialize with
#    README / LICENSE / .gitignore — the bundle already has those.
#    Click "Create repository". Copy the repo URL.

# 2. Point this clone at the new remote and push:
git remote add origin <paste-the-url-here>
git push -u origin main
```

If `git push` complains about safe-directory ownership (can happen
after extracting across volumes), run this once and retry:

```bash
git config --global --add safe.directory "$(pwd)"
```

## Option C — Web-UI hand upload

No git needed locally:

```bash
unzip paper3.zip
```

Then on github.com:

1. Create a new empty repo (click `+` → New repository, **do** check
   "Add a README file" — gives you something to upload into).
2. Open the repo, click "Add file" → "Upload files".
3. Drag the contents of the unpacked `paper3/` directory onto the
   page (or upload by subfolder: `core/`, `data/`, `scripts/`,
   `tests/`, plus the top-level files).
4. After upload, edit the auto-generated README on the web, delete
   its stub content, then upload `README.md` from the bundle to
   replace it.
5. The hand-upload loses the prepared commit history (you'll get one
   commit per upload batch). Options A and B preserve the single
   clean "Initial commit" entry, which looks better as a paper
   supplementary link.

## Suggested repo metadata (paste into the GitHub UI after creation)

- **Description:** "Experiment harness for Arithmetic-Aligned Decoding
  (AAD) on receipt KIE — supports DONUT / LayoutLMv3 via a small
  adapter contract."
- **Topics:** `key-information-extraction`, `receipts`, `sroie`,
  `cord`, `constrained-decoding`, `document-ai`
- **Visibility:** private until paper acceptance, then flip to public.

## Sanity check after pushing

```bash
git clone <your-new-repo-url> /tmp/paper3-check
cd /tmp/paper3-check
pip install -r requirements.txt
python -m paper3.tests.test_smoke
# Expected: "All smoke tests passed." in <10 s
```

If smoke tests pass on the freshly cloned repo, the migration is
complete and reproducible.
