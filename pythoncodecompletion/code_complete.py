#!/usr/bin/env python

# Copyright (C) 2011 Luke Benstead
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

""" A code completion parser for Python """

from StringIO import StringIO
import tokenize
import keyword
import __builtin__

from token import DEDENT, NEWLINE

class ScopeType:
    MODULE = 1
    CLASS = 2
    METHOD = 3

KEYWORDS_THAT_INHERIT_SCOPE = [ "if", "else", "for", "elif", "try", "except", "do", "while", "with" ]
KEYWORDS_THAT_ARE_IGNORED = [ "raise", "assert", "break", "continue", "throw", "print", "pass", "return" ]

class Scope(object):
    def __init__(self, name, scope_type, parent=None):
        self.name = name
        self.scope_type = scope_type
        self.parent = parent
        
        self.variables = set()
        self.methods = set()
        self.types = set()
        self.keywords = set()
        
        if scope_type == ScopeType.MODULE:
            self.methods = set([ x for x in dir(__builtin__) if __builtins__.get(x).__class__ == isinstance.__class__ ])
            self.types = set([ x for x in dir(__builtin__) if isinstance(__builtins__.get(x), type) ])
            self.keywords = set(keyword.kwlist)
        self.modules = set()
        self.inherited_scopes = set()

        self.children = {}
        
    def inherit(self, scope):
        import copy
        self.inherited_scopes.add(copy.deepcopy(scope))

    def get_variables(self):
        result = list(self.variables)
        for scope in self.inherited_scopes:
            if isinstance(scope, Scope):
                result.extend(scope.get_variables())
            else:
                #FIXME: look up class scope
                pass
        return set(result)
    
    def get_methods(self):
        result = list(self.methods)
        for scope in self.inherited_scopes:
            if isinstance(scope, Scope):        
                result.extend(scope.get_methods())
            else:
                #FIXME: look up class scope
                pass                
        return set(result)
    
    def get_types(self):
        result = list(self.types)
        for scope in self.inherited_scopes:
            if isinstance(scope, Scope):        
                result.extend(scope.get_types())
            else:
                #FIXME: look up class scope
                pass                
        return set(result)        
    
class ObjectScope(Scope):
    def __init__(self, parent):
        super(ObjectScope, self).__init__("object", ScopeType.CLASS, parent=parent)
        
        attrs = dir(object)
        methods = [ x for x in attrs if callable(getattr(object, x, None)) ]
        variables = [ x for x in attrs if not callable(getattr(object, x, None)) ]
        
        self.variables = set(variables)
        self.methods = set(methods)
        self.types = set()
        self.keywords = set()

class ListScope(Scope):
    def __init__(self, parent):
        super(ListScope, self).__init__("list", ScopeType.CLASS, parent=parent)
        
        attrs = dir(list)
        methods = [ x for x in attrs if callable(getattr(list, x, None)) if not x.startswith("__") ]
        variables = [ x for x in attrs if not callable(getattr(list, x, None)) if not x.startswith("__") ]
        
        self.variables = set(variables)
        self.methods = set(methods)

class TupleScope(Scope):
    def __init__(self, parent):
        super(TupleScope, self).__init__("tuple", ScopeType.CLASS, parent=parent)
        
        attrs = dir(tuple)
        methods = [ x for x in attrs if callable(getattr(tuple, x, None)) if not x.startswith("__")]
        variables = [ x for x in attrs if not callable(getattr(tuple, x, None)) if not x.startswith("__") ]
        
        self.variables = set(variables)
        self.methods = set(methods)

class IntScope(Scope):
    def __init__(self, parent):
        super(IntScope, self).__init__("int", ScopeType.CLASS, parent=parent)
        
        attrs = dir(int)
        methods = [ x for x in attrs if callable(getattr(int, x, None)) if not x.startswith("__")]
        variables = [ x for x in attrs if not callable(getattr(int, x, None)) if not x.startswith("__") ]
        
        self.variables = set(variables)
        self.methods = set(methods)

class StrScope(Scope):
    def __init__(self, parent):
        super(StrScope, self).__init__("str", ScopeType.CLASS, parent=parent)
        
        attrs = dir(str)
        methods = [ x for x in attrs if callable(getattr(str, x, None)) if not x.startswith("_")]
        variables = [ x for x in attrs if not callable(getattr(str, x, None)) if not x.startswith("_") ]
        
        self.variables = set(variables)
        self.methods = set(methods)

class DictScope(Scope):
    def __init__(self, parent):
        super(DictScope, self).__init__("dict", ScopeType.CLASS, parent=parent)
        
        attrs = dir(dict)
        methods = [ x for x in attrs if callable(getattr(dict, x, None)) if not x.startswith("__")]
        variables = [ x for x in attrs if not callable(getattr(dict, x, None)) if not x.startswith("__") ]
        
        self.variables = set(variables)
        self.methods = set(methods)
                
                
class FileParser(object):
    def __init__(self, file_contents, current_line=None):
        self._line_no = 0
        self._global = Scope("__global__", ScopeType.MODULE)
        self._current_scope = self._global
        self._current_line = current_line
        self._active_scope = self.get_global_scope()
        self._do_parse(file_contents)

    def _parse_to_end(self):
        tokens = []
        ignore_rest = False
        while True:
            tok_type, token, line = self._get_next_token()
            
            if tok_type == tokenize.COMMENT:
                print "COMMENT"
                ignore_rest = True
            
            if not ignore_rest:
                tokens.append((tok_type, token))

            if tok_type == NEWLINE or token == "\n":
                break;
        return tokens
    
    def _parse_class(self):
        tok_type, token, line = self._get_next_token()
        
        class_name = token
        class_scope = Scope(token, ScopeType.CLASS, parent=self._current_scope)
        self._current_scope.types.add(class_name) #Store this class as a type
        self._current_scope.children[class_name] = class_scope
        self._current_scope = class_scope
        print "New scope: %s at line %s" % (self._current_scope.name, self._line_no)
        tokens = self._parse_to_end()

        #We have an open bracket, this means the class has parents
        if tokens and tokens[0][1] == "(":
            tokens = tokens[1:]
            for tok_type, token in tokens[:]: 
                if tokens[0][1] == ":": 
                    break
                
                tokens = tokens[1:]
                if token == ")": break
                if token == ",": continue
                
                self._current_scope.inherited_scopes.add(token)

        #If at this point tokens[0] is a colon, we need to check and see if there are any other statements
        #after it, if so, we need to dedent
        if tokens and tokens[0][1] == ":":
            if len(tokens) > 1 and tokens[1][1] != "\n":
                #Ignore everything after the colon, but dedent, this is likely something like:
                # class B(object): pass
                self._dedent()

    def _parse_method(self):
        tok_type, token, line = self._get_next_token()

        method_name = token
        
        method_scope = Scope(token, ScopeType.METHOD, parent=self._current_scope)
            
        self._current_scope.methods.add(method_name) #Store this class as a type        
        self._current_scope.children[method_name] = method_scope
        self._current_scope = method_scope
        
        print "New scope: %s at line %s" % (self._current_scope.name, self._line_no)

        tokens = self._parse_to_end()
        
        tokens = [ x for x in tokens if x[1] not in ("(", ",", ")", ":") ]


        if not tokens: 
            return

        class_scope = self._find_parent_scope_of_type(ScopeType.CLASS)
        if class_scope: #This is a method that has a parent class
            #Grab the first argument (normally "self")
            first_token_type, first_token = tokens[0]            
            
            tokens = tokens[1:] #Remove from the tokens list
            print "CLASS VAR: ", class_scope.name, first_token
            
            #add it to the variables list
            self._current_scope.variables.add(first_token)
            #set the scope for the variable as that of the parent class (so self.whatever works)
            assert(isinstance(class_scope, Scope))
            self._current_scope.children[first_token] = class_scope
        
        #The type of all other args are anybody's guess, so just treat them as "object"s
        for tok_type, token in tokens:
            #generic object scope
            self._current_scope.children[token] = ObjectScope(parent=self._current_scope)
            self._current_scope.variables.add(token)

    def _parse_with(self):
        while True:
            tok_type, token_str, line = self._get_next_token()
            if tok_type == NEWLINE:
                break
                
            #If we find the "as" token, we know the next token is the variable name
            if token_str == "as":
                tok_type, token_str, line = self._get_next_token()
                if tok_type == NEWLINE:
                    break;
                self._current_scope.variables.add(token_str)
                break
        
        self._parse_to_end()


    def _parse_statement(self, lvalue_type, lvalue):
        """ FIXME handle multiple lvalues"""
        
        tokens = [(lvalue_type, lvalue)] + self._parse_to_end()

        is_assignment_statement = False
        equals_position = None
        i = 0
        for token in tokens:
            if token[1] == "=":
                is_assignment_statement = True
                equals_position = i
                break
            i += 1
                
        is_assignment_to_member = lvalue == "self"
        
        scope = self._current_scope
        
        if is_assignment_statement:
            lvalue_tokens = [ x for x in tokens[:equals_position] if x[1] not in (",",) ]
            rvalue_tokens = [ x for x in tokens[equals_position + 1:] if x[1] not in (",",) ]
            if is_assignment_to_member:
                class_scope = self._find_parent_scope_of_type(ScopeType.CLASS)
                if not class_scope:
                    print("Don't understand this: " + str(tokens))
                    if self._current_scope:
                        print(self._current_scope.name)
                        print(self._current_scope.parent.name)
                    else:
                        print("NO CURRENT SCOPE!")
                    return 
                else:
                    scope = class_scope
            assert(isinstance(scope, Scope))
            if len(lvalue_tokens) == 1 or is_assignment_to_member:
                if is_assignment_to_member:
                    lvalue_name = lvalue_tokens[2][1] # [ 'self', '.', 'something' ]
                else:
                    lvalue_name = lvalue_tokens[0][1]
                scope.variables.add(lvalue_name)
                if rvalue_tokens[0][1] == "[":
                    scope.children[lvalue_name] = ListScope(self._current_scope)
                elif rvalue_tokens[0][1] == "(":
                    scope.children[lvalue_name] = TupleScope(self._current_scope)
                elif rvalue_tokens[0][1] == "{":
                    scope.children[lvalue_name] = DictScope(self._current_scope)                        
                elif rvalue_tokens[0][0] == tokenize.NUMBER:
                    scope.children[lvalue_name] = IntScope(self._current_scope)
                elif rvalue_tokens[0][0] == tokenize.STRING:
                    scope.children[lvalue_name] = StrScope(self._current_scope)
            else:
                print "TODO: Handle assignment: ", lvalue_tokens, "=", rvalue_tokens

    def _find_parent_scope_of_type(self, scope_type):
        current = self._current_scope
        while current.scope_type != scope_type and current.parent:
            current = current.parent
            
        if current.scope_type != scope_type:
            return None
            
        return current
    
    def _dedent(self):
        to_dedent = self._dedent_stack.pop()
        
        if to_dedent:
            if self._current_scope.parent:
                self._current_scope = self._current_scope.parent
                print "New scope: %s at line %s" % (self._current_scope.name, self._line_no)
        else:
            print "Ignoring dedent at %s" % self._line_no
    
    def _get_next_token(self):
        while True:
            tok_type, token, (lineno, indent), end, line = self._gen.next()    	
            print token
            if token == "\n" or tok_type == tokenize.NEWLINE: 
                self._line_no += 1
            elif "\n" in token:
                self._line_no += token.count("\n")

            if tok_type == DEDENT:
                self._dedent()
                continue
            else:
                break

        return tok_type, token, line
    
    def _get_next_token(self):
        tok_type, token, (lineno, indent), end, line = self._gen.next()    	
        if token == "\n" or token == tokenize.NEWLINE: 
            self._line_no += 1
		
        print self._line_no, "DEDENT" if tok_type == tokenize.DEDENT else token, line
        return tok_type, token, line
    
    def _do_parse(self, file_contents):
        buf = StringIO(file_contents)
        self._gen = tokenize.generate_tokens(buf.readline)
        
        in_block_without_scope = 0
        self._line_no = 0
        self._dedent_stack = []
        
        while True:
            try:
                tok_type, token, line = self._get_next_token()
                                
#                print line, lineno, self._current_line
                if self._current_line == self._line_no:
                    self._active_scope = self._current_scope

                if token == "#" or tok_type == tokenize.COMMENT:
                    self._parse_to_end()
                elif tok_type == tokenize.STRING:
                    self._parse_to_end()
                elif tok_type == tokenize.STRING:
                    self._line_no += token.count("\n")
                    self._parse_to_end()
                elif token == "class":
                    print("Pushing dedent: %s" % True)                
                    self._dedent_stack.append(True)
                    self._parse_class()
                elif token == "def":
                    print("Pushing dedent: %s" % True)
                    self._dedent_stack.append(True)
                    self._parse_method()
                elif token in KEYWORDS_THAT_INHERIT_SCOPE:                   
                    tokens = self._parse_to_end()
                    token_types = [x[0] for x in tokens ]
                    block_finished = False
                    if tokenize.COLON in token_types:
                        colon_idx = token_types.index(tokenize.COLON)
                        tokens_after_colon = [ x for x in token_types[colon_idx+1:] if x not in (tokenize.NEWLINE,) ]
                        if len(tokens_after_colon):
                            print "IF LINE: ", tokens_after_colon
                            block_finished = True 
                    print("Pushing dedent: %s" % block_finished)
                    self._dedent_stack.append(block_finished)
                    
                elif token in KEYWORDS_THAT_ARE_IGNORED:
                    self._parse_to_end()
                elif token in keyword.kwlist:
                    print "Unhandled keyword: '" + token + "'"
                    self._parse_to_end()
                else:
                    if token.strip():
                        self._parse_statement(tok_type, token)

            except StopIteration:
                break
        
    def get_global_scope(self):
        return self._global
        
    def get_active_scope(self):
        return self._active_scope or self.get_global_scope()

class Completer(object):
    def __init__(self):
        self._parsers = {}
        self._active_parser = None
        
    def parse_file(self, name, file_content, line):
        try:
            parser = FileParser(file_content, current_line=line)
        except (IndentationError, tokenize.TokenError):
            pass
        else:
            self._parsers[name] = parser
        if name in self._parsers:
            self._active_parser = name
    
    def get_completions(self, match):
    	"""
    		Get the completions for match, using the location of the
    		current_line to detect the current scope
    	"""
    	
        print("Completing: " + match)
        if not self._active_parser:
            return []
            
        parser = self._parsers[self._active_parser]
        scope_at_line = parser.get_active_scope()
        
        parts = match.split(".")
        all_possible = set()
        print "Scope: " + scope_at_line.name
        all_possible.update(scope_at_line.get_variables())
        all_possible.update(scope_at_line.get_methods())
        all_possible.update(scope_at_line.get_types())        
    
        if match in all_possible:
            all_possible.remove(match) #Don't include the match
                        
        matches = []
        
        global_matches = set()                
        global_matches.update(parser.get_global_scope().get_variables())
        global_matches.update(parser.get_global_scope().get_methods())
        global_matches.update(parser.get_global_scope().get_types())
        
        if match in global_matches:
            global_matches.remove(match) #Don't include the match        
        
        for possible in global_matches:
            if possible.startswith(match) or not match.strip():
                matches.append(possible)
        
        for part in parts:        
            if part in all_possible and part in scope_at_line.children:
                scope_at_line = scope_at_line.children[part]
                print "Looking at scope: " + scope_at_line.name                
                matches = []
                
                all_possible = set()
                all_possible.update(scope_at_line.get_variables())
                all_possible.update(scope_at_line.get_methods())
                all_possible.update(scope_at_line.get_types())                

                if match in all_possible:
                    all_possible.remove(match) #Don't include the match
            else:
                for possible in all_possible:
                    if possible.startswith(part):
                        matches.append(possible)
                break
                        
        return sorted(list(set(matches)))

c = Completer()
def complete(file_content, match, line):
    c.parse_file("test", file_content, line)
    return [ { 'abbr' : x } for x in c.get_completions(match) ]

if __name__ == '__main__':
    sample = """
    class A(object):
        class_var = 2
    
        def __init__(self):
            self._var_1 = None
            var1, var2 = (a, b)
            
        def _private(self):
            pass
            
        def public(self, other):
            self._var_1 = 1
            var2 = 2
            
            def submethod(_something):
                pass
                
            with open("x.txt") as f:
                data = f.read()
                
            if self == other:
                g = 1
                
            try:
                pass
            except Something:
                pass
            except Something, e:
                pass
            except (Something, SomethingElse):
                pass
            except (Something, SomethingElse), e:
                pass
    
    class B: pass
    class C(object): pass
    
    def main():
        a = A()
    """
    
    matches = complete(sample, "va", 6)
    print "Matches are: %s" % matches
    matches = complete(sample, "se", 6)
    print "Matches are: %s" % matches
    matches = complete(sample, "self.", 6)
    print "Matches are: %s" % matches

    parser = FileParser(sample)
    global_scope = parser.get_global_scope()
    
    assert global_scope.name == "__global__"
    assert "A" in global_scope.types
    assert "B" in global_scope.types
    assert "main" in global_scope.methods

    assert "A" in global_scope.children
    assert "__init__" in global_scope.children["A"].methods
    assert "_private" in global_scope.children["A"].methods
    assert "public" in global_scope.children["A"].methods
    assert "class_var" in global_scope.children["A"].variables
    
    assert "a" in global_scope.children["main"].variables
    assert "submethod" in global_scope.children["A"].children["public"].methods
    assert "f" in global_scope.children["A"].children["public"].variables
    
    assert "self" in global_scope.children["A"].children["public"].variables
    assert "self" in global_scope.children["A"].children["public"].children
    
    #Self should inherit the parent class scope
    assert "public" in global_scope.children["A"].children["public"].children["self"].methods
    
    #Unknown variables should inherit the "object" scope and so should contain __class__ etc.
    assert "__class__" in global_scope.children["A"].children["public"].children["other"].methods

    assert "g" in global_scope.children["A"].children["public"].variables
