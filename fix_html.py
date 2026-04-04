import re
import pathlib

files = [
    'ui/components/profile.py',
    'ui/components/scores.py',
    'ui/components/tier.py',
    'ui/components/questions.py',
]

for fpath in files:
    p = pathlib.Path(fpath)
    src = p.read_text(encoding='utf-8')

    # Handle the pattern:
    #   st.markdown(
    #       <content lines>,
    #       unsafe_allow_html=True,
    #   )
    # where content may span multiple lines via string concatenation
    src = re.sub(
        r'st\.markdown\(\s*\n(\s+)(.*?)\n\s+unsafe_allow_html\s*=\s*True,?\s*\n\s*\)',
        lambda m: 'st_html(\n' + m.group(1) + m.group(2) + '\n' + m.group(1)[:-4] + ')',
        src,
        flags=re.DOTALL,
    )

    p.write_text(src, encoding='utf-8')
    print(f'Updated: {fpath}')

print('Done.')
