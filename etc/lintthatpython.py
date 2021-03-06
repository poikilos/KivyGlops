#!/usr/bin/env python3

import sys
import os
import re

#see https://stackoverflow.com/questions/16982625/only-accept-alphanumeric-characters-and-underscores-for-a-string-in-python#16982669
if sys.version_info >= (3, 0):
    _w = re.compile("^\w+$", re.A)  # str.isalnum(this_char) or this_char=="_"
else:
    _w = re.compile("^\w+$")  # str.isalnum(this_char) or this_char=="_"

def find_not_any(haystack, needle_chars):
    result = -1
    needle_chars_len = len(needle_chars)
    for i in range(0, len(haystack)):
        found = False
        for index in range(needle_chars_len):
            if needle_chars[index] == haystack[i]:
                found = True
                break
        if not found:
            result = i
            break
    return result

def split_non_quoted(line, splitters, inline_comment_marker="#"):
    results = None
    if line is not None:
        line = line.strip()
        if len(line) > 0:
            results = []
            in_quote = None
            start_i = 0
            i = 0
            while i < len(line) + 1:
            #for i in range(0, len(line)+1):
                forced_past_enable = False
                if (i>=len(line)) or ((in_quote is None) and (str(line[i]) in splitters)):
                    results.append(line[start_i:i])
                    #if (i>=len(line)):
                    #    print("appending end '"+line[start_i:i]+"'")  # debug only
                    #else:
                    #    print("appending chunk '"+line[start_i:i]+"'")  # debug only
                    #start_i = i + 1
                    while (i<len(line)) and (line[i] in splitters):
                        i += 1
                        forced_past_enable = True
                    start_i = i
                elif (in_quote is None) and (line[i]=='"' or line[i]=="'"):
                    in_quote = line[i]
                elif (in_quote is None) and (line[i]==inline_comment_marker):
                    results.append(line[start_i:i])
                    #print("appending before comment '"+line[start_i:i]+"'")  # debug only
                    start_i = i + 1
                    break
                elif (in_quote is not None) and (line[i]==in_quote):
                    in_quote = None
                if not forced_past_enable:
                    i += 1
        else:
            print("#WARNING: blank line in split_non_quoted")
    else:
        print("#WARNING: line is None in split_non_quoted")
    return results

number_parts = "-0123456789."
def is_number(s):
    s = str(s)
    for c in s:
        if c not in number_parts:
            return False
    return True

def find_non_quoted(line, needle, inline_comment_marker="#", debug_list=None):
    result = -1
    if line is not None:
        if needle is not None:
            needle_len = len(needle)
            haystack_len = len(line)
            if len(line) > 0:
                in_quote = None
                for i in range(0, len(line)):
                    if i + needle_len > haystack_len:
                        break
                    elif (in_quote is None) and line[i:i+needle_len]==needle:
                        if debug_list is not None:
                            debug_list.append("#needle " + needle + " is at " + str(i) + " in '" + line + "'")  # debug only
                        result = i
                        break
                    elif (in_quote is None) and (line[i]=='"' or line[i]=="'"):
                        in_quote = line[i]
                    elif (in_quote is None) and (line[i]==inline_comment_marker):
                        break
                    elif (in_quote is not None) and (line[i]==in_quote):
                        in_quote = None
        else:
            #print("#WARNING: skipped trying to find needle None in '" + line + "'")
            print("#WARNING: skipped trying to find needle None")
    return result

def file_to_list(filename):
    ret = None
    if os.path.isfile(filename):
        ret = []
        ins = open(filename, 'r')
        line = True
        while line:
            line = ins.readline()
            if line:
                line_strip = line.strip()
                if len(line_strip) > 0:
                    ret.append(line_strip)
        ins.close()
    return ret

def list_to_file(filename, l, remove_repeats=False):
    outs = open(filename, 'w')
    big_d = {}
    for line in l:
        line_enable = True
        if remove_repeats:
            if big_d.get(line) is True:
                line_enable = False
            big_d[line] = True
        if line_enable:
            outs.write(line + "\n")

    outs.close()

def lint_that_python_project(folder_path):
    results = []
    for sub_name in os.listdir(folder_path):
        sub_path = os.path.join(folder_path, sub_name)
        if sub_name[:1]!=".":
            if os.path.isdir(sub_path):
                results.extend(lint_that_python_project(sub_path))
            elif sub_path[-3:] == '.py':
                results.extend(lint_that_python(sub_path))
    return results

def lint_that_python(filename):
    if os.path.isdir(filename):
        print("# (lintthatpython verbose message) detected directory," +
              "sending to lint_that_python_project...")
        lint_that_python_project(filename)
        return
    results = []
    user_classes = []
    user_methods = []
    user_symbols = []
    print("# (lintthatpython verbose message) started '" + filename +
          "'")
    more_user_symbols = file_to_list('user_symbols.txt')
    if more_user_symbols is not None:
        user_symbols.extend(more_user_symbols)
    # TODO: lint string continuations in brackets like could happen
    # below if a comma is missed at the end of a line!
    kivy_syms = ['require', 'Clock', 'schedule',
                 'properties',
                 'NumericProperty', 'StringProperty', 'ListProperty',
                 'ObjectProperty', 'BooleanProperty',
                 'BoundedNumericProperty', 'OptionProperty',
                 'ReferenceListProperty', 'AliasProperty',
                 'DictProperty',
                 'Vector', 'vector', 'App', 'app', 'Color',
                 'ContextInstruction', 'kivy', 'uix',
                 'Mesh',
                 'vertices', 'indices', 'fmt', 'mode',
                 'Label', 'Factory', 'factory', 'core',
                 'window', 'Window',
                 'on_motion', 'on_touch_down',
                 'Keyboard',
                 'bind', 'unbind', 'on_key_up', 'on_key_down',
                 'Logger', 'logger',
                 'Widget', 'widget',
                 'canvas', 'color', 'opacity', 'size', 'size_hint',
                 'Button',
                 'on_press',
                 'providers', 'mouse', 'MouseMotionEvent',
                 'InstructionGroup',
                 'floatlayout', 'FloatLayout', 'boxlayout', 'BoxLayout',
                 'Translate', 'Rotate', 'Scale', 'BindTexture',
                 'PushMatrix', 'PopMatrix', 'MatrixInstruction',
                 'Matrix', 'view_clip', 'translate', 'look_at',
                 'RenderContext', 'shader', 'source',
                 'resource_find', 'content', 'auto_dismiss', 'title',

                 'Popup',
                 'image', 'Image', 'opengl', 'transformation',
                 'graphics',
                 'glEnable', 'glDisable']
    builtin_syms = ['basename', '__name__', '__file__',
                     '__author__',  '__init__','callable',
                    'dirname', 'abspath', 'normpath', 'os',
                    'str',
                    'rstrip', 'lstrip', 'strip',
                    'dict', 'list',
                    'sorted', 'deepcopy', 'copy', 'append',
                    'get', 'items',
                    'randrange', 'choice', 'listdir',
                    'math', 'pi', 'sqrt', 'degrees', 'radians',
                    'time', 'None', 'True', 'False',
                    'range', 'exit', 'find', 'copy2', 'makedirs',
                    'environ',
                    "\\",  'float', 'int', 'input',
                    'open', 'write', 'readline', 'close',
                    'isfile',
                    'traceback', 'exc_info', 'print_tb',
                    'str', 'clock', 'super',
                    'button', 'join', 'sys', 'getcwd', 'item',
                    'getattr', 'lower', 'self',
                    'largs', 'kwargs']
    pygments_syms = ['lexers', 'GLShaderLexer']
    # first line has function-like statements:
    builtin_keywords = ['del', 'import', 'def', 'class',
                        'pass', 'from', 'as', 'global',
                        'try', 'except', 'raise',
                        'if', 'elif', 'else', 'for', 'while',
                        'and', 'or', 'not', 'is', 'in',
                        'return',  'continue', 'break']
    tkinter_syms = ['Label', 'Button', 'Frame', 'TOP', 'LEFT',
                    'BOTTOM', 'RIGHT']

    builtin_syms.extend(builtin_keywords)
    builtin_syms.extend(tkinter_syms)
    builtin_syms.extend(pygments_syms)
    # NOT used (Python 2):
    # first line has function-like statements:
    builtin_py2_keywords = ['print']
    builtin_py2_syms = ['iteritems', 'itervalues', 'viewitems',
                        'xrange']
    # TODO: check for use of `%` string operator deprecated in Python 3
    # builtin_syms.extend(builtin_py2_keywords)
    # builtin_syms.extend(builtin_py2_syms)
    kivy_enable = True
    if kivy_enable:
        builtin_syms.extend(kivy_syms)
        print("# (lintthatpython verbose message) Adding Kivy symbols (allowing kivy symbols to be" +
              " considered spelled correctly).")

    if os.path.isfile(filename):
        print("processing '" + filename + "'")
        class_names_var_lists = {}
        class_names_method_lists = {}
        unique = {}  # if a word is only used once, it may be mispelled
        for pass_i in range(0,2):
            ins = open(filename, 'r')
            line_original = True
            spaces_ever_found = False
            tabs_ever_found = False
            line_number = 1
            mixed_tabs_and_spaces_msg_enable = True
            in_class_name = None
            in_function_name = None
            in_function_indent = None
            in_multiline_name = None
            comment = None
            in_multiline_quotes = None
            while line_original:
                line_original = ins.readline()
                if line_original:
                    indent_end = find_not_any(line_original, [" ", "\t"])
                    if indent_end >= 0:
                        line = line_original.rstrip()
                        line_strip = line.strip()

                        if in_multiline_quotes is not None:
                            multiline_end = line.find(in_multiline_quotes)
                            if multiline_end > -1:
                                in_multiline_quotes = None
                        else:
                            comment_i = find_non_quoted(line, "#")
                            comment = None
                            if comment_i > -1:
                                comment = line[comment_i:]
                                line = line[0:comment_i]
                            line_strip = line.strip()
                            if (pass_i==1):
                                bad_mark_i = find_non_quoted(line, ";")
                                if bad_mark_i > -1:
                                    print(filename+"("+str(line_number)+","+str(bad_mark_i)+"): semicolon in statement is not valid in python")
                            if line_strip[0:1] != "#":
                                ces_msg_enable = False
                                if len(line_strip) > 0:
                                    indent = line[0:indent_end]
                                    if " " in indent:
                                        spaces_ever_found = True
                                    if "\n" in indent:
                                        tabs_ever_found = True
                                    if spaces_ever_found and tabs_ever_found:
                                        if mixed_tabs_and_spaces_msg_enable:
                                            print(filename+"("+str(line_number)+",0): inconsistent use of tabs and spaces")
                                            mixed_tabs_and_spa
                                    if len(indent) == 0:
                                        in_class_name = None
                                        in_function_name = None
                                    if in_function_name is not None:
                                        if len(indent) < len(in_function_indent):
                                            in_function_indent = None
                                            in_function_name = None
                                    scope_by_indent = None
                                    if tabs_ever_found:
                                        scope_by_indent = len(indent)
                                    elif spaces_ever_found:
                                        scope_by_indent = int(len(indent)/4)  # assumes 4 spaces per tab
                                    if scope_by_indent is None:
                                        # ok to have no indent before ever having indent
                                        scope_by_indent = 0
                                    #print("#splitting '" + line_strip + "'")  # debug only
                                    multiline_start_i = find_non_quoted(line, "'''")
                                    multiline_alt_start_i = find_non_quoted(line, '"""')
                                    if multiline_start_i > -1:
                                        in_multiline_quotes = "'''"
                                        #TODO: get variable name before it
                                    elif multiline_alt_start_i > -1:
                                        in_multiline_quotes = '"""'
                                        #TODO: get variable name before it
                                    else:
                                        chunks = split_non_quoted(line_strip, [" ", "\t"])
                                        if pass_i == 1:
                                            symbols = split_non_quoted(line_strip, [" ", "\t", ".", ":", "{", "}", "[", "]", ",", "+", "-", "*", "/", "%", "(", ")", ">", "<", "="])
                                            for symbol_orig in symbols:
                                                symbol = symbol_orig.strip()
                                                user_symbol = True
                                                if len(symbol) < 1:
                                                    user_symbol = False
                                                elif is_number(symbol):
                                                    user_symbol = False
                                                elif symbol in user_classes:
                                                    # count as spelled
                                                    # correctly if defined
                                                    user_symbol = False
                                                elif symbol in user_methods:
                                                    # count as spelled
                                                    # correctly if defined
                                                    user_symbol = False
                                                elif symbol in user_symbols:
                                                    # count as spelled
                                                    # correctly if specified
                                                    user_symbol = False
                                                elif ((len(symbol) > 1) and
                                                        (symbol[0]=='"') and
                                                        (symbol[-1]=='"')):
                                                    user_symbol = False
                                                elif ((len(symbol) > 1) and
                                                        (symbol[0]=="'") and
                                                        (symbol[-1]=="'")):
                                                    user_symbol = False
                                                elif ((len(symbol) > 2) and
                                                        (symbol[:2]=="b'") and
                                                        (symbol[-1]=="'")):
                                                    # Python 3 bytestring
                                                    user_symbol = False
                                                elif ((len(symbol) > 1) and
                                                        (symbol[:2]=='b"') and
                                                        (symbol[-1]=='"')):
                                                    # Python 3 bytestring
                                                    user_symbol = False
                                                elif symbol in builtin_syms:
                                                    user_symbol = False
                                                if user_symbol:
                                                    if symbol in unique:
                                                        unique[symbol] += 1
                                                    else:
                                                        unique[symbol] = 1

                                        if chunks is not None:
                                            if len(chunks) > 0:
                                                if chunks[0] == "class":
                                                    in_function_name = None
                                                    if len(chunks) > 1:
                                                        paren_i = find_non_quoted(chunks[1], "(")
                                                        colon_i = find_non_quoted(chunks[1], ":")
                                                        class_name_end_i = None
                                                        if paren_i > -1:
                                                            class_name_end_i = paren_i
                                                        elif colon_i > -1:
                                                            class_name_end_i = colon_i
                                                        if class_name_end_i is not None:
                                                            in_class_name = chunks[1][0:class_name_end_i].strip()
                                                            if pass_i == 0:
                                                                if in_class_name not in user_classes:
                                                                    user_classes.append(in_class_name)
                                                                    print("# (lintthatpython verbose message) added to user_classes: " + in_class_name)
                                                            # if (pass_i==1):
                                                            #     results.append("#in class '" + in_class_name + "'")
                                                        else:
                                                            if (pass_i==1):
                                                                results.append(filename+"("+str(line_number)+",0): class name not followed by '(' or ':'")
                                                    else:
                                                        if (pass_i==1):
                                                            results.append(filename+"("+str(line_number)+",0): class without name")
                                                elif chunks[0] == "def":
                                                    if len(chunks) > 1:
                                                        paren_i = find_non_quoted(chunks[1], "(")
                                                        if paren_i > -1:
                                                            in_function_name = chunks[1][0:paren_i].strip()
                                                            if pass_i==0:
                                                                if in_function_name not in user_methods:
                                                                    user_methods.append(in_function_name)
                                                            in_function_indent = indent
                                                            if (pass_i==0):
                                                                if not (in_class_name in class_names_method_lists):
                                                                    class_names_method_lists[in_class_name] = []
                                                                class_names_method_lists[in_class_name].append(in_function_name)
                                                        else:
                                                            if (pass_i==1):
                                                                results.append(filename+"("+str(line_number)+",0): def name not followed by '('")
                                                    else:
                                                        if (pass_i==1):
                                                            results.append(filename+"("+str(line_number)+",0): def without name")
                                                elif (in_class_name is not None) and (in_function_name is None):
                                                    sign_i = find_non_quoted(line_strip, "=")
                                                    if sign_i > -1:
                                                        variable_name = line_strip[:sign_i].strip()
                                                        if (pass_i==0):
                                                            if (" " not in variable_name) and ("\t" not in variable_name):
                                                                if not (in_class_name in class_names_var_lists):
                                                                    class_names_var_lists[in_class_name] = []
                                                                class_names_var_lists[in_class_name].append(variable_name)
                                                            else:
                                                                if (pass_i==1):
                                                                    results.append(filename+"("+str(line_number)+",0): whitespace in variable name '"+variable_name+"'")
                                                    else:
                                                        if line_strip[0:1] != "@" and line_strip != "pass":
                                                            if (pass_i==1):
                                                                results.append(filename+"("+str(line_number)+",0): statement '"+line_strip+"' in class is neither variable nor decorator nor pass")
                                                else:
                                                    #else should be a statement
                                                    if (pass_i==1):
                                                        if (in_class_name is not None):
                                                            foreign_found = False
                                                            for key in class_names_var_lists:
                                                                if key != in_class_name:
                                                                    for i in range(0, len(class_names_var_lists[key])):
                                                                        foreign_i = find_non_quoted(line, "self."+class_names_var_lists[key][i])
                                                                        if foreign_i > -1:
                                                                            foreign_end = foreign_i + len("self."+class_names_var_lists[key][i])
                                                                            if (foreign_end==len(line)) or (not re.match(_w, line[foreign_end])):
                                                                                if (foreign_end<len(line)) and (not re.match(_w, line[foreign_end])):
                                                                                    #results.append("#"+filename+"("+str(line_number)+","+str(foreign_end)+"): '"+line[foreign_end]+"' is not alphanumeric")
                                                                                    results.append(filename+"("+str(line_number)+","+str(foreign_i)+"): possibly ambiguous variable '"+class_names_var_lists[key][i]+"' from other class '"+key+"' in same file used via self by class '"+in_class_name+"'")
                                                                                    break
                                                                    if key in class_names_method_lists:
                                                                        #use same key since already on it
                                                                        for i in range(0, len(class_names_method_lists[key])):
                                                                            foreign_i = find_non_quoted(line, "self."+class_names_method_lists[key][i])
                                                                            if foreign_i > -1:
                                                                                foreign_end = foreign_i + len("self."+class_names_method_lists[key][i])
                                                                                if (foreign_end==len(line)) or (not re.match(_w, line[foreign_end])):
                                                                                    results.append(filename+"("+str(line_number)+",0): possibly ambiguous method '"+class_names_method_lists[key][i]+"' from other class '"+key+"' in same file used via self by class '"+in_class_name+"'")
                                                                                    break
                                            else:
                                                if (pass_i==1):
                                                    results.append(filename+"("+str(line_number)+",0): (PARSER ERROR) got 0 chunks for line")
                                        else:
                                            if (pass_i==1):
                                                results.append(filename+"("+str(line_number)+",0): (PARSER ERROR) chunks is None for line")
                                    #end else not multiline opener
                                else:
                                    #if (pass_i==1):
                                    #   results.append("#"+filename+"("+str(line_number)+",0): [debug only] skipped blank line")
                                    pass  # blank line
                            else:
                                #if (pass_i==1):
                                #   results.append("#"+filename+"("+str(line_number)+",0): [debug only] skipped comment")
                                pass  # comment
                        #end else multiline comment
                    #else blank line with just indents
                line_number += 1
            ins.close()
            msg = ""
            for k,v in unique.items():
                if v == 1:
                    msg += " '" + k + "'"
            if len(msg) > 0:
                print("# (lintthatpython warning) " + filename +
                      ":" +
                      " only occur once:" +
                      " '" + msg + "'")
        #end for pass_i
    else:
        results.append(filename+"(0,0): FILE NOT FOUND")
    return results

if (sys.argv is not None) and (len(sys.argv)>0):
    for i in range(0, len(sys.argv)):
        if sys.argv[i] == __file__:
            #print("(running " + __file__ + ")")
            pass
        elif sys.argv[i][0:2]=="--":
            if False:
                pass # put known options here
            else:
                print("STOPPED before processing since found unknown option " + sys.argv[i])
                usage()
                exit(1)
        else:
            if os.path.isfile(sys.argv[i]):
                results = lint_that_python(sys.argv[i])
                error_count = 0
                for result in results:
                    if (result is not None) and (len(result)>0):
                        if (result[0:1]!="#"):
                            error_count += 1
                        print(result)
                print(str(error_count)+" error(s) in '" + sys.argv[i] + "'")
            elif os.path.isdir(sys.argv[i]):
                results = lint_that_python_project(sys.argv[i])
                error_count = 0
                for result in results:
                    if (result is not None) and (len(result)>0):
                        if (result[0:1]!="#"):
                            error_count += 1
                        print(result)
                print(str(error_count)+" error(s) in '" + sys.argv[i] + "'")
            else:
                print(__file__+" ERROR: unknown option or missing file '" + sys.argv[i] + "'")


