from copy import copy
from reportlab.lib.units import cm

class Rect:
    """ 
    To hold dimensions of a rect: top, bottom, left, right.

    Can instantiate with height or width and one other parameter
    on each dimension.

    Height, width always calculated, and area

    Can overwrite left / right, top / bottom and width / height
    recalculated

    Can hold direction for how to draw inside:
        from_bottom, from_right
        (default is from top left, ie leaving gap at bottom or right
         if the drawing made is not the same dims as the rect)

    Reports the shape: height / width
    """
    def __init__(self, bottom=None, top=None, height=None,
                 left=None, right=None, width=None,
                 from_bottom=False, from_right=False,
                 name=None):

        # x dims first
        self.left = left
        self.right = right
        self.width = width

        if self.width is None and (left and right):
            self.width = right - left

        elif self.left is None and (right and width):
            self.left = right - width

        elif self.right is None and (left and width):
            self.right = left + width

        # y dims
        self.top = top
        self.bottom = bottom
        self.height = height

        if self.height is None and (top and bottom):
            self.height = top - bottom

        elif self.bottom is None and (top and height):
            self.bottom = top - height

        elif self.top is None and (bottom and height):
            self.top = bottom + height

        # other stuff
        self.from_bottom = from_bottom
        self.from_right = from_right
        self.name = name

    @property
    def left(self):
        return self.__left

    @left.setter
    def left(self, value):
        # need to adjust the width but only if right already set
        if self.__dict__.get("_Rect__right") is not None and value is not None:
            if value > self.right:
                raise ValueError('cant have a negative width')
            self.width = self.right - value
        self.__left = value

    @property
    def right(self):
        return self.__right

    @right.setter
    def right(self, value):
        # need to adjust the width but only if left already set
        if self.__dict__.get("_Rect__left") is not None and value is not None:
            if value < self.left:
                raise ValueError('cant have a negative width')
            self.width = value - self.left
        self.__right = value

    @property
    def top(self):
        return self.__top

    @top.setter
    def top(self, value):
        # need to adjust the width but only if bottom already set
        if self.__dict__.get("_Rect__bottom") is not None and value is not None:
            if value < self.bottom:
                raise ValueError('cant have a negative height')
            self.height = value - self.bottom
        self.__top = value

    @property
    def bottom(self):
        return self.__bottom

    @bottom.setter
    def bottom(self, value):
        # need to adjust the height but only if top already set
        if self.__dict__.get("_Rect__top") is not None and value is not None:
            if value > self.top:
                raise ValueError('cant have a negative height')
            self.height = self.top - value
        self.__bottom = value

    @property
    def width_cm(self):
        return self.width * cm

    @property
    def height_cm(self):
        return self.height * cm

    @property
    def area(self):
        return abs(self.height * self.width)

    @property
    def shape(self):
        return self.height / self.width
    
    @property
    def x(self):
        return self.left
    
    @property
    def x_cm(self):
        return self.left * cm
    
    @property
    def y(self):
        return self.bottom

    @property
    def y_cm(self):
        return self.bottom * cm

    @property
    def dims(self):
        """
        Return the dims ready to pass to canvas.Rect
        """
        return [self.x, self.y, self.width, self.height]

    def __mul__(self, value):
        """ 
        Return a new rect with all dimensions multiplied by the passed value
        """

        out = copy(self)
        for k, v in out.__dict__.items():
            out.__dict__[k] = v * value

        return out

    def new(self, left=None, right=None, top=None, bottom=None):
        """
        Return a copy with the passed parameter changed
        """
        out = copy(self)

        if left is not None:
            out.left = left

        if right is not None:
            out.right = right

        if top is not None:
            out.top = top

        if bottom is not None:
            out.bottom = bottom

        return out
        

    def fit_to_max(self, height, width):
        """ 
        Returns a rect fitted to a passed height and width,
        without changing the shape
        """

        # work out which dimension needs to scale most and do that one only
        # if image shape too tall, means need to scale to the height
        if self.shape > height / width:
            return self * (height / self.height)

        # image too wide, scale to the width
        elif self.shape < height / width:
            return self * (width / self.width)

        return copy(self)

    def draw(self, canvas):
        """
        Just draw it as a rect on the passed canvas
        """
        canvas.rect(self.x*cm, self.y*cm, self.width*cm, self.height*cm)

    def __repr__(self):
        return (
            "Rect("
            f"bottom={round(self.bottom, 2)}, "
            f"top={round(self.top, 2)}, "
            f"height={round(self.height, 2)}, "
            f"left={round(self.left, 2)}, "
            f"right={round(self.right, 2)}, "
            f"width={round(self.width, 2)}"
            ")"
        )
