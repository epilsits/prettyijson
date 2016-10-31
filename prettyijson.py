import sublime
import sublime_plugin
from io import StringIO
import sys
import os

sys.path.append(os.path.dirname(__file__))
import ijson

class BaseIndentCommand(sublime_plugin.TextCommand):
  
    def __init__(self, view):
        self.view = view
        self.settings = sublime.load_settings("PrettyiJson.sublime-settings")

    def get_language(self):
        syntax = self.view.settings().get('syntax')
        language = splitext(basename(syntax))[0].lower() if syntax is not None else "plain text"
        return language

    def check_enabled(self, lang):
        return True

    def is_enabled(self):
        """
        Enables or disables the 'indent' command. Command will be disabled if
        there are currently no text selections and current file is not 'XML' or
        'Plain Text'. This helps clarify to the user about when the command can
        be executed, especially useful for UI controls.
        """
        return False if self.view is None or \
            (self.settings.get("restrict_lang", False) and not self.check_enabled(self.get_language())) \
            else True

    def run(self, edit):
        """
        Main plugin logic for the 'indent' command.
        """
        view = self.view
        regions = view.sel()
        # if there are more than 1 region or region one and it's not empty
        if len(regions) > 1 or not regions[0].empty():
            for region in view.sel():
                if not region.empty():
                    s = view.substr(region).strip()
                    s = self.indent(s)
                    if s:
                        view.replace(edit, region, s)
        else:  # format all text
            alltextreg = sublime.Region(0, view.size())
            s = view.substr(alltextreg).strip()
            s = self.indent(s)
            if s:
                view.replace(edit, alltextreg, s)
                view.run_command("detect_indentation")


class PrettyIjsonCommand(BaseIndentCommand):

    def check_enabled(self, language):
        return ((language == "json") or (language == "plain text"))

    def indent(self, s):
        settings_indent = self.settings.get("json_indent", 4)
        if isinstance(settings_indent, int):
            indent_string = ''.ljust(settings_indent)
        else:
            indent_string = settings_indent
        
        try:
            indent = ""
            lenIndent = len(indent_string)
            prevEvent = ""
            with StringIO(s) as sIn, StringIO() as sOut:
                parser = ijson.parse(sIn, do_translate=False)
                for prefix, event, value in parser:
                    if event == "start_map":
                        if prevEvent.startswith("end_"):
                            sOut.seek(sOut.tell() - 1)
                            sOut.write(" ")

                        sOut.write("{\n")
                        indent += indent_string
                    elif event == "end_map":
                        if prevEvent == "start_map":
                            sOut.seek(sOut.tell() - 1)
                            sOut.write("},\n")
                            indent = indent[:-lenIndent]
                        else:
                            sOut.seek(sOut.tell() - 2)
                            sOut.write("\n")
                            indent = indent[:-lenIndent]
                            sOut.write(indent + "},\n")
                    elif event == "start_array":
                        if prevEvent.startswith("end_"):
                            sOut.seek(sOut.tell() - 1)
                            sOut.write(" ")

                        sOut.write("[")
                        indent += indent_string
                    elif event == "end_array":
                        if prevEvent == "start_array":
                            sOut.write("],\n")
                            indent = indent[:-lenIndent]
                        elif prevEvent == "end_map":
                            sOut.seek(sOut.tell() - 2)
                            sOut.write("\n")
                            indent = indent[:-lenIndent]
                            sOut.write(indent + "],\n")
                        else:
                            sOut.seek(sOut.tell() - 2)
                            sOut.write("],\n")
                            indent = indent[:-lenIndent]
                    elif event == "map_key":
                        sOut.write(indent + '"' + value + '"' + ": ")
                    else:
                        if prevEvent == "end_map":
                            sOut.seek(sOut.tell() - 1)
                            sOut.write(" ")
                        
                        if event == "null":
                            sOut.write("null,")
                        elif event == "boolean":
                            sOut.write(str(value).lower() + ",")
                        elif event == "number":
                            sOut.write(value + ",")
                        elif event == "string":
                            sOut.write('"' + value + '"' + ",")

                        sOut.write("\n" if prevEvent == "map_key" else " ")
                    
                    prevEvent = event

                sOut.seek(sOut.tell() - 2)
                sOut.truncate()
                return sOut.getvalue()
        except ijson.JSONError as err:
            message = "Invalid JSON: %s" % (err)
            sublime.status_message(message)
            return
