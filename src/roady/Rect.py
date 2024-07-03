from copy import copy

class Rect:
    """ 
    To hold dimensions of a rect: top, bottom, left, right.

    Can instantiate with height or width and one other parameter
    on each dimension.

    Height, width always calculated, and area

    Reports the shape: height / width
    """
    def __init__(self, bottom=None, top=None, height=None,
                 left=None, right=None, width=None):

        self.bottom = bottom
        self.top = top
        self.left = left
        self.right = right

        if self.bottom is None and (top and height):
            self.bottom = top - height

        if self.top is None and (bottom and height):
            self.top = bottom + height

        if self.left is None and (right and width):
            self.left = right - width

        if self.right is None and (left and width):
            self.right = left + width

    @property
    def height(self):
        return self.top - self.bottom

    @property
    def width(self):
        return self.right - self.left

    @property
    def area(self):
        return abs(self.height * self.width)

    @property
    def shape(self):
        return self.height / self.width

    def __mul__(self, value):
        """ 
        Return a new rect with all dimensions multiplied by the passed value
        """

        out = copy(self)
        for k, v in out.__dict__.items():
            out.__dict__[k] = v * value

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

    def __repr__(self):
        return (
            "Rect("
            f"bottom={self.bottom}, "
            f"top={self.top}, "
            f"height={self.height}, "
            f"left={self.left}, "
            f"right={self.right}, "
            f"width={self.width}"
            ")"
        )
