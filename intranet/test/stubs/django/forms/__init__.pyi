class Form:
  # FIXME: figure out args
  def __init__(self, *args, **kwargs): ...
class ModelForm(Form): ...
class Field:
  # FIXME: figure out args
  def __init__(self, *args, **kwargs): ...
class CharField(Field): ...
class IntegerField(Field): ...
class ModelMultipleChoiceField(Field): ...
class ModelChoiceField(Field): ...
class DateField(Field): ...
class BooleanField(Field): ...
class ChoiceField(Field): ...
class FileField(Field): ...
class Textarea:
  # FIXME: figure out args
  def __init__(self, *args, **kwargs): ...
class DateTimeInput: ...
class TextInput:
  # FIXME: figure out args
  def __init__(self, *args, **kwargs): ...
