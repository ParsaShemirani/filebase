## Naming:
- Will name derivatives <original_id>{proxy}.ext


## Text files
- No proxies as of now

## Images
- Highest level image (Either RAW or camera JPG)
- Extreme low quality ( 1000 px width, 32 level compression)

## Videos
- Original video
- Heavily compressed: h.264, crf 32, 1000px width, medium preset
- Contact sheet, 4x4 grid

## Audio
- Original Audio
- Extreme low quality, mono. (-ac 1 -q:a 7)



/Users/parsahome/main/inbox/image_compress/1397.jpg

sips "/Users/parsahome/main/inbox/image_compress/1397.jpg" \
  --resampleWidth 1000 \
  --setProperty format jpeg \
  --setProperty formatOptions 32 \
  --out "/Users/parsahome/main/inbox/image_compress/1397_1000px.jpg"
