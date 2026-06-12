# Clone https://github.com/adunning/bedes-bible
# and convert to JSON and plaintext
import re,json
from pathlib import Path
from git import Repo
from lxml import etree

# HTTPS clone point:
remote = 'https://github.com/adunning/bedes-bible.git'
# Desired target folder name:
local = Path('bedes-bible')
# XML namespaces:
ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

# Invalid documents:
invalid = [
        '0979r-colossenes-cap.xml'
        ]

def extract():
    # Clone XML repository if not already present:
    if not(local.is_dir()):
        repo = Repo.clone_from(remote, local)
    # Else, just update the working copy from remote:
    else:
        repo = Repo(local)
        assert isinstance(repo, Repo)
        repo.remotes.origin.pull()
    assert not repo.bare

    # Set to desired outputs:
    plaintext_folder = Path('amiatinus-plain')
    json_out = Path('amiatinus.json')
    bible = dict()
    
    # Normalization matrix
    substitutions = {
        'ę': 'æ',
        '·': ''
    }

    discard = ['am', 'sic', 'del', 'note', 'surplus', 'orig', 'fw', 'label', 'rdg']  
    ignore = ['lb', 'cb', 'pb']
    query = ['{http://www.tei-c.org/ns/1.0}' + i for i in discard]
    milestones = ['{http://www.tei-c.org/ns/1.0}' + i for i in ignore]
    
    # Token normalization:
    def normalize(token):
        # Lowercase:
        token = token.lower()
        for k,v in substitutions.items():
            # Carry out replacements:
            token = token.replace(k, v)
        return token
    
    # Discarding the content of unwanted XML elements:
    def simplify(branch):
        for hit in branch.iter(query):
            for element in hit.iter():
                element.text = ''
                ancestry = [element.xpath('ancestor::tei:' + i, namespaces=ns) for i in discard]
                if any(ancestry):
                    element.tail = ''
        return branch
    
    # Load the corpus into a multidimensional dictionary/list structure:
    print('Loading XML corpus...')
    parser = etree.XMLParser(remove_blank_text=False,resolve_entities=True)
    Path(plaintext_folder).mkdir(parents=True, exist_ok=True)
    corpus = dict()
    xml_folder = Path(local / 'text')
    for file in sorted(xml_folder.glob('*.xml')):
        if not file.name in invalid:
            basename = file.name[:-4]
            basename = basename.split('-', 1)[1]
            tree = etree.parse(file, parser=parser)
            root = simplify(tree.getroot())
            text = root.find('{http://www.tei-c.org/ns/1.0}text')
            for ref in text.iter('{http://www.tei-c.org/ns/1.0}milestone'):
                ref.text = '\n' + ref.get('n') + ': '
            for section in ['{http://www.tei-c.org/ns/1.0}p', '{http://www.tei-c.org/ns/1.0}div']:
                for div in text.iter(section):
                    if div.text is not None:
                        div.text = '\n' + div.text
            for milestone in text.iter(milestones):
                if (not milestone.get('break') == 'no') and milestone.tail is not None:
                    milestone.tail = ' ' + milestone.tail
                elif (not milestone.get('break') == 'no') and milestone.tail is None:
                    milestone.tail = ' '

            segments = dict()
            rubric_counter = 0
            doc_string = normalize(etree.tostring(text, method='text', encoding='unicode'))
            doc_string = re.sub(r'\n{1,3}(\D)', r'\1', doc_string)
            doc_string = re.sub(r'\n *\n', r'\n', doc_string)
            doc_string = re.sub(r' {2,}', ' ', doc_string)
            doc_string = re.sub(r'\n ', r'\n', doc_string)
            if '\n' in doc_string:
                doc_string = doc_string.split('\n', 1)[1]
            outfile = Path(plaintext_folder / str(basename + '.txt'))
            with open(outfile, 'w') as f:
                f.write(doc_string)
            verses = doc_string.split('\n')
            rubric_counter = 0
            bible[basename] = dict()
            for verse in verses:
                if ': ' in verse[:10]:
                    ref = verse.split(': ', 1)[0]
                    text = verse.split(': ', 1)[1]
                else:
                    rubric_counter += 1
                    ref = 'rubric' + str(rubric_counter)
                    text = verse
                if not re.search(r'^ *$', text):
                    bible[basename][ref] = text

    with open(json_out, 'w') as f:
        json.dump(bible, f, ensure_ascii=False, indent=4)
    
if __name__ == '__main__':
    extract()
