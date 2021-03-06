# -*- coding: utf-8 -*-
import re
import os
import shutil
import json
import argparse


class DocumentationGenerator:

    def __init__(self, args):
        self.template_dir = args.templates
        self.target_dir = args.sources
        self.project_name = args.project + '/'
        self.language = args.language
        self.docs_root = args.docs_root
        self.source_code_path = args.code
        self.github_root = ('https://github.com/deeplearning4j/deeplearning4j/tree/master/'
                            + self.source_code_path[3:])

        with open(self.project_name + 'pages.json', 'r') as f:
            json_pages = f.read()
        site = json.loads(json_pages)
        self.pages = site.get('pages', [])
        self.indices = site.get('indices', [])
        self.excludes = site.get('excludes', [])



    def class_to_docs_link(self, module_name, class_name):
        return self.docs_root + module_name.replace('.', '/') + '#' + class_name


    def class_to_source_link(self, module_name, cls_name):
        return '[[source]](' + self.github_root + module_name + '/' + cls_name + '.' + self.language + ')'


    def to_code_snippet(self, code):
        return '```' + self.language + '\n' + code + '\n```\n'


    def process_main_docstring(self, doc_string):
        lines = doc_string.split('\n')
        doc = [line.replace('*', '').lstrip(' ').rstrip('/') for line in lines[1:-1] if not '@' in line]
        return '\n'.join(doc)


    def process_docstring(self, doc_string):
        lines = doc_string.split('\n')
        doc = [line.replace('*', '').lstrip(' ').replace('@', '- ') for line in lines]
        return '\n'.join(doc)


    def render(self, signature, doc_string, class_name, is_method):
        if is_method:  # Method name from signature
            method_regex = r'public [static\s]?[a-zA-Z0-9]* ([a-zA-Z0-9]*)\('
            name = re.findall(method_regex, signature)[0]
        else: # Constructor takes class name
            name = class_name
        sub_blocks = ['<b>{}</b> \n{}'.format(name, self.to_code_snippet(signature))]
        if doc_string:
            sub_blocks.append(doc_string + '\n')
        return '\n\n'.join(sub_blocks)


    def get_main_doc_string(self, class_string, class_name):
        doc_regex = r'\/\*\*\n([\S\s]*?.*)\*\/\n'  # match "/** ... */" at the top
        doc_string = re.search(doc_regex, class_string)
        try:
            doc_match = doc_string.group();
        except:
            doc_match = ''
        doc = self.process_main_docstring(doc_match)
        if not doc_string:
            print('Warning, no doc string found for class {}'.format(class_name))
        doc_index = 0 if not doc_match else doc_string.end()
        return doc, class_string[doc_index:]


    def get_constructor_data(self, class_string, class_name):
        constructors = []
        if 'public ' + class_name in class_string:
            while 'public ' + class_name in class_string:
                doc_regex = r'\/\*\*\n([\S\s]*?.*)\*\/\n[\S\s]*?(public ' \
                            + class_name + '.[\S\s]*?){'
                result = re.search(doc_regex, class_string)
                doc_string, signature = result.groups()
                doc = self.process_docstring(doc_string)
                class_string = class_string[result.end():]
                constructors.append((signature, doc))
        return constructors, class_string

    def get_public_method_data(self, class_string):
        method_regex = r'public [static\s]?[a-zA-Z0-9]* ([a-zA-Z0-9]*)\('
        method_strings = re.findall(method_regex, class_string)

        methods = []
        for method in method_strings:
            doc_regex = r'\/\*\*\n([\S\s]*?.*)\*\/\n[\S\s]*?' + \
                        '(public [static\s]?[a-zA-Z0-9]* ' + method + '[\S\s]*?){'
            result = re.search(doc_regex, class_string)
            doc_string, signature = result.groups()
            doc = self.process_docstring(doc_string)
            class_string = class_string[result.end():]
            methods.append((signature, doc))
        return methods

    def inspect_class_string(self, module, cls):
        return self.read_file(self.source_code_path + module + '/' + cls)


    def read_index_data(self, data):
        module_index = data.get('module_index', "")
        modules = os.listdir(self.project_name + self.target_dir + '/' + module_index)
        modules = [mod.replace('.md', '') for mod in modules if mod != 'index.md']
        index_string = ''.join('- [{}](./{})\n'.format(mod.title().replace('-', ' '), mod) for mod in modules if mod)
        print(index_string)
        return  ['', index_string]

    def read_page_data(self, data):
        if data.get('module_index', ""):  # indices are created after pages
            return []
        page_data = []
        classes = []

        module = data.get('module', "")
        if module:
            classes = os.listdir(self.source_code_path + module)

        cls = data.get('class', "")
        if cls:
            classes = cls

        for cls in sorted(classes):
            class_string = self.inspect_class_string(module, cls)
            class_string = class_string.replace('<p>', '').replace('</p>', '')
            class_name = cls.replace('.' + self.language, '')
            doc_string, class_string = self.get_main_doc_string(class_string, class_name)
            constructors, class_string = self.get_constructor_data(class_string, class_name)
            methods = self.get_public_method_data(class_string)

            page_data.append([module, class_name, doc_string, constructors, methods])

        return page_data


    def clean_target(self):
        if os.path.exists(self.project_name + self.target_dir):
            shutil.rmtree(self.project_name + self.target_dir)

        for subdir, dirs, file_names in os.walk(self.project_name + self.template_dir):
            for file_name in file_names:
                new_subdir = subdir.replace(self.project_name + self.template_dir, self.project_name + self.target_dir)
                if not os.path.exists(new_subdir):
                    os.makedirs(new_subdir)
                if file_name[-3:] == '.md':
                    file_path = os.path.join(subdir, file_name)
                    new_file_path = file_path.replace(
                        self.project_name + self.template_dir, self.project_name + self.target_dir
                    )
                    shutil.copy(file_path, new_file_path)


    def read_file(self, path):
        with open(path) as f:
            return f.read()


    def create_index_page(self):
        readme = self.read_file(self.project_name + 'README.md')
        index = self.read_file(self.project_name + 'templates/index.md')
        # if readme has a '##' tag, append it to index
        index = index.replace('{{autogenerated}}', readme[readme.find('##'):])
        with open(self.project_name + self.target_dir + '/index.md', 'w') as f:
            f.write(index)

    def write_content(self, blocks, page_data):
        assert blocks, 'No content for page ' + page_data['page']

        markdown = '\n----\n\n'.join(blocks)
        path = os.path.join(self.project_name + self.target_dir, page_data['page'])

        if os.path.exists(path):
            template = self.read_file(path)
            assert '{{autogenerated}}' in template, \
                    'Template found for {} but missing {{autogenerated}} tag.'.format(path)
            markdown = template.replace('{{autogenerated}}', markdown)
        print('Auto-generating docs for {}'.format(path))
        markdown = markdown
        subdir = os.path.dirname(path)
        if not os.path.exists(subdir):
            os.makedirs(subdir)
        with open(path, 'w') as f:
            f.write(markdown)


    def prepend_headers(self):
        for subdir, dirs, file_names in os.walk(self.project_name + self.target_dir):
            for file_name in file_names:
                if file_name[-3:] == '.md':
                    file_path = os.path.join(subdir, file_name)
                    header = '---\ntitle: {}\nlayout: default\n---\n'.format(file_name.replace('.md', ''))
                    with open(file_path, 'r+') as f:
                        content = f.read()
                        f.seek(0, 0)
                        f.write(header.rstrip('\r\n') + '\n' + content)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--project', '-p', type=str, required=True)  # e.g. keras-import
    parser.add_argument('--code', '-c', type=str, required=True)  # relative path to source code for this project

    parser.add_argument('--language', '-l', type=str, required=False, default='java')
    parser.add_argument('--docs_root', '-d', type=str, required=False, default='http://deeplearning4j.org') # TBD
    parser.add_argument('--templates', '-t', type=str, required=False, default='templates')
    parser.add_argument('--sources', '-s', type=str, required=False, default='doc_sources')

    args = parser.parse_args()
    doc_generator = DocumentationGenerator(args)

    doc_generator.clean_target()
    doc_generator.create_index_page()

    for page_data in doc_generator.pages:
        data = doc_generator.read_page_data(page_data)
        blocks = []
        for module_name, class_name, doc_string, constructors, methods in data:
            class_string = doc_generator.inspect_class_string(module_name, class_name + '.' + doc_generator.language)
            # skip class if it contains any exclude keywords
            if not any(ex in class_string for ex in doc_generator.excludes):
                sub_blocks = []
                link = doc_generator.class_to_source_link(module_name, class_name)
                sub_blocks.append('<span style="float:right;"> {} </span>'.format(link))
                if module_name:
                    sub_blocks.append('## {}\n'.format(class_name))

                if doc_string:
                    sub_blocks.append(doc_string)

                if constructors:
                    sub_blocks.append('\n---\n<b>Constructors</b>\n\n---\n'.join(
                        [doc_generator.render(cs, cd, class_name, False) for (cs, cd) in constructors])
                    )

                if methods:
                    sub_blocks.append('\n---\n<b>Methods</b>\n\n---\n'.join(
                        [doc_generator.render(ms, md, class_name, True) for (ms, md) in methods])
                    )
                blocks.append('\n'.join(sub_blocks))

        doc_generator.write_content(blocks, page_data)

    for index_data in doc_generator.indices:
        index = doc_generator.read_index_data(index_data)
        doc_generator.write_content(index, index_data)

doc_generator.prepend_headers()
