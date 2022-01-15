from jinja2 import Template, Environment, FileSystemLoader


class Page_Template(object):
    def __init__(self, template_file, base_path='./', txt_fomat='utf8') -> None:
        self.env = Environment(loader=FileSystemLoader(
            base_path, encoding=txt_fomat))
        self.update_tmpl(template_file)

    def update_tmpl(self, template_file):
        self.template_file = template_file
        self.tmpl = self.env.get_template(template_file)

    def render(self, params):
        page = self.tmpl.render(params)
        page = ''.join([l.strip() for l in page.split('\n')])
        return page
