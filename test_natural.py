import cr_natural as N
import pytest
@pytest.mark.parametrize('text,command',[
 ('turn on voice','/voice on'),('call me Sam','/nickname Sam'),('be more concise','/persona concise'),('quiz me','/play quiz'),('research solar panels in the background','/work brief solar panels'),('set quiet hours to 9pm until 8am','/quiet_hours 21 8'),('show work number 12','/work show 12'),('connect my docs account','connect workspace'),('read aloud Hello there','/speak Hello there')])
def test_plain_routes(text,command):assert N.translate(text)==command
@pytest.mark.parametrize('text',['send this email','delete all files','transfer money','read my inbox','call someone','buy a car'])
def test_no_effect_guess(text):assert N.translate(text)==text
