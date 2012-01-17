#!/usr/bin/env python
""" A code completion parser for Python """

from StringIO import StringIO
import tokenize
from token import DEDENT, NEWLINE

class ScopeType:
    MODULE = 1
    CLASS = 2
    METHOD = 3

class Scope(object):
    def __init__(self, name, scope_type, parent=None):
        self.name = name
        self.scope_type = scope_type
        self.parent = parent
        
        self.variables = []
        self.methods = []
        self.types = []
        self.keywords = []
        self.modules = []
        
        self.children = {}

class Parser(object):
    def __init__(self, file_contents):
        self._global = Scope("__global__", ScopeType.MODULE)
        self._current_scope = self._global
        self._do_parse(file_contents)
        
    def _parse_to_end(self, until=None):
        while True:
            tok_type, token, (lineno, indent), end, line = self._gen.next()

            if tok_type == DEDENT:
                if self._current_scope.parent:
                    self._current_scope = self._current_scope.parent
                    print "New scope: " + self._current_scope.name
                                    
            if tok_type == NEWLINE:
                break;
    
    def _parse_class(self):
        type, token, (lineno, indent), end, line = self._gen.next()
        
        class_name = token
        print "Found class: " + class_name
        self._current_scope.types.append(class_name) #Store this class as a type
        
        class_scope = Scope(token, ScopeType.CLASS, parent=self._current_scope)
        self._current_scope.children[class_name] = class_scope
        self._current_scope = class_scope
        print "New scope: " + self._current_scope.name        
        return self._parse_to_end()
        
    def _parse_method(self):
        type, token, (lineno, indent), end, line = self._gen.next()
        
        method_name = token
        print "Found method: " + method_name
        self._current_scope.methods.append(method_name) #Store this class as a type
        
        method_scope = Scope(token, ScopeType.METHOD, parent=self._current_scope)
        self._current_scope.children[method_name] = method_scope
        self._current_scope = method_scope
        
        print "New scope: " + self._current_scope.name
        #FIXME: Add passed arguments to the method scope
        return self._parse_to_end()

    def _parse_with(self):
        while True:
            tok_type, token, (lineno, indent), end, line = self._gen.next()
            if tok_type == NEWLINE:
                break;
                
            #If we find the "as" token, we know the next token is the variable name
            if token == "as":
                tok_type, token, (lineno, indent), end, line = self._gen.next()
                if tok_type == NEWLINE:
                    break;
                self._current_scope.variables.append(token)
                break
        
        self._parse_to_end()

        
    def _parse_statement(self, lvalue):
        tokens = [lvalue]
        while True:
            tok_type, token, (lineno, indent), end, line = self._gen.next()
            tokens.append(token)
            if tok_type == NEWLINE:
                break;

        scope = self._current_scope        
        if tokens[0] == "self":
            class_scope = self._find_parent_scope_of_type(ScopeType.CLASS)
            if not class_scope:
                print("Don't understand this: " + str(tokens))
                print(self._current_scope.name)
                print(self._current_scope.parent.name)
                return 
            else:
                scope = class_scope

        for token in tokens:
            if token not in ("self", ",", "(", ")"):
                scope.variables.append(token)
            if token == "=":
                break
        
    def _find_parent_scope_of_type(self, scope_type):
        current = self._current_scope
        while current.scope_type != scope_type and current.parent:
            current = current.parent
            
        if current.scope_type != scope_type:
            return None
            
        return current
    
    def _do_parse(self, file_contents):
        import keyword
        
        buf = StringIO(file_contents)
        self._gen = tokenize.generate_tokens(buf.readline)
        
        while True:
            try:
                tok_type, token, (lineno, indent), end, line = self._gen.next()
                
                if tok_type == DEDENT:
                    if self._current_scope.parent:
                        self._current_scope = self._current_scope.parent
                        print "New scope: " + self._current_scope.name

                if not token.strip() or tok_type == tokenize.COMMENT:
                    continue

                if token == "pass":
                    self._parse_to_end()
                    continue
                elif token == "#":
                    self._parse_to_end()
                elif token == "class":
                    last_line_incomplete = not self._parse_class()
                elif token == "def":
                    last_line_incomplete = not self._parse_method()
                elif token == "with":
                    self._parse_with()
                elif token in keyword.kwlist:
                    print "Unhandled keyword: " + token
                else:
                    self._parse_statement(token)

            except StopIteration:
                break
        
    def get_global_scope(self):
        return self._global

class Completer(object):

    def add_module(self, python_file):
        pass
        
    def get_completions(self, match, python_file, line):
        pass
    
if __name__ == '__main__':
    sample = """
    class A(object):
        class_var = 2
    
        def __init__(self):
            self._var_1 = None
            var1, var2 = (a, b)
            
        def _private(self):
            pass
            
        def public(self):
            self._var_1 = 1
            var2 = 2
            
            def submethod(_something):
                pass
                
            with open("x.txt") as f:
                data = f.read()
    
    def main():
        a = A()
    """

    parser = Parser(sample)
    global_scope = parser.get_global_scope()
    
    assert global_scope.name == "__global__"
    assert "A" in global_scope.types
   # assert "B" in global_scope.types
    assert "main" in global_scope.methods

    assert "A" in global_scope.children
    assert "__init__" in global_scope.children["A"].methods
    assert "_private" in global_scope.children["A"].methods
    assert "public" in global_scope.children["A"].methods
    assert "class_var" in global_scope.children["A"].variables
    
    assert "a" in global_scope.children["main"].variables
    assert "submethod" in global_scope.children["A"].children["public"].methods
    assert "f" in global_scope.children["A"].children["public"].variables
    

