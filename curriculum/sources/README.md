# Raw frequency corpora

The large raw `*.txt` frequency lists live here but are **git-ignored** (they're
regenerable). Only the processed `../italian-frequency.json` is committed.

To (re)fetch the Italian source and rebuild the curriculum:

```bash
curl -sSL -o it_full.txt \
  "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/it/it_full.txt"

cd ..
python3 build_frequency.py --source sources/it_full.txt --out italian-frequency.json --top 6000
```

Source: [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords)
(OpenSubtitles 2018, MIT). Other languages live under `content/2018/<lang>/`.
