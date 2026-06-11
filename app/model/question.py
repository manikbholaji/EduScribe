class Question:
    def __init__(self, id_num, text="", marks=1, image_path=None):
        self.id = id_num
        self.text = text
        self.marks = marks
        self.image_path = image_path

    def __repr__(self):
        return f"Q{self.id}: {self.text[:20]}... ({self.marks} marks)"