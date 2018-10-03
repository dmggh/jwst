"""This module contains utility functions for generating HTML using
Python code rather than a template engine.  Encoding your HTML this
way enables the Python compiler to check some of the basic form
automatically and ensures everything will be properly nested.  Since
close tags are automatically provided and attributes are automatically
converted and quoted, it is easier to write than HTML or template code.

>>> p
_Tag('p')

>>> print p("this is a paragraph")
<p>this is a paragraph</p>

>>> print p("a\\nmultiline\\nparagraph\\n")
<p>a
multiline
paragraph
</p>

>>> print div("more text", size="+1", another=999)
<div another='999' size='+1'>more text</div>

WARNING:  this module overrides builtin functions:
 input
 dir
 map
 object
"""
class _Tag(object):
    """Represents an HTML tag of the same name,  and when called
    brackets the contents in the tag,  formatting any additional
    keyword parameters as tag attributes.
    """
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "_Tag(" + repr(self.name) + ")"

    def __call__(self, contents, **attrs):
        result = "<" + self.name + " "
        for k, v in list(attrs.items()):
            if k.startswith("_"):
                k = k[1:]
            result += k + "='" + str(v) + "' "
        result = result[:-1] + ">"
        result += contents
        result += "</" + self.name + ">"
        return result

# Define HTML tag globals

a  = _Tag('a')
abbr  = _Tag('abbr')
acronym  = _Tag('acronym')
address  = _Tag('address')
applet  = _Tag('applet')
area  = _Tag('area')
b  = _Tag('b')
base  = _Tag('base')
basefont  = _Tag('basefont')
bdo  = _Tag('bdo')
big  = _Tag('big')
blockquote  = _Tag('blockquote')
body  = _Tag('body')
br  = _Tag('br')
button  = _Tag('button')
caption  = _Tag('caption')
center  = _Tag('center')
cite  = _Tag('cite')
code  = _Tag('code')
col  = _Tag('col')
colgroup  = _Tag('colgroup')
dd  = _Tag('dd')

x_del  = _Tag('del')

dfn  = _Tag('dfn')
dir  = _Tag('dir')
div  = _Tag('div')
dl  = _Tag('dl')
dt  = _Tag('dt')
em  = _Tag('em')
fieldset  = _Tag('fieldset')
font  = _Tag('font')
form  = _Tag('form')
frame  = _Tag('frame')
frameset  = _Tag('frameset')
head  = _Tag('head')
h1  = _Tag('h1')
h2  = _Tag('h2')
h3  = _Tag('h3')
h4  = _Tag('h4')
h5  = _Tag('h5')
h6  = _Tag('h6')
hr  = _Tag('hr')
html  = _Tag('html')
i  = _Tag('i')
iframe  = _Tag('iframe')
img  = _Tag('img')
input  = _Tag('input')
ins  = _Tag('ins')
kbd  = _Tag('kbd')
label  = _Tag('label')
legend  = _Tag('legend')
li  = _Tag('li')
link  = _Tag('link')
map  = _Tag('map')
menu  = _Tag('menu')
meta  = _Tag('meta')
noframes  = _Tag('noframes')
noscript  = _Tag('noscript')
object  = _Tag('object')
ol  = _Tag('ol')
optgroup  = _Tag('optgroup')
option  = _Tag('option')
p  = _Tag('p')
param  = _Tag('param')
pre  = _Tag('pre')
q  = _Tag('q')
s  = _Tag('s')
samp  = _Tag('samp')
script  = _Tag('script')
select  = _Tag('select')
small  = _Tag('small')
span  = _Tag('span')
strike  = _Tag('strike')
strong  = _Tag('strong')
style  = _Tag('style')
sub  = _Tag('sub')
sup  = _Tag('sup')
table  = _Tag('table')
tbody  = _Tag('tbody')
td  = _Tag('td')
textarea  = _Tag('textarea')
tfoot  = _Tag('tfoot')
th  = _Tag('th')
thead  = _Tag('thead')
title  = _Tag('title')
tr  = _Tag('tr')
tt  = _Tag('tt')
u  = _Tag('u')
ul  = _Tag('ul')
var  = _Tag('var')

# ============================================================

def _test():
    import doctest
    from pyetc.etc_web.etc import html as doctest_html
    return doctest.testmod(doctest_html)

if __name__ == "__main__":
    print(_test())
