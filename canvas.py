"""
This file is for the tkinter canvas that draws the output of the HQ Trivia Bot.
"""

from tkinter import Tk, Canvas, Frame, BOTH, CENTER, LEFT, W, E, StringVar, Button, IntVar

# This code is used to draw rounded rectangles in tkinter
def round_rectangle(x1, y1, x2, y2, canvas, radius=25, **kwargs):

    points = [x1+radius, y1,
              x1+radius, y1,
              x2-radius, y1,
              x2-radius, y1,
              x2, y1,
              x2, y1+radius,
              x2, y1+radius,
              x2, y2-radius,
              x2, y2-radius,
              x2, y2,
              x2-radius, y2,
              x2-radius, y2,
              x1+radius, y2,
              x1+radius, y2,
              x1, y2,
              x1, y2-radius,
              x1, y2-radius,
              x1, y1+radius,
              x1, y1+radius,
              x1, y1]

    return canvas.create_polygon(points, **kwargs, smooth=True)

class MainCanvas(Frame):

    def __init__(self):
        super().__init__()
        self.question = StringVar()
        self.answer_1 = StringVar()
        self.answer_2 = StringVar()
        self.answer_3 = StringVar()
        self.method_1 = StringVar()
        self.method_2 = StringVar()
        self.method_3 = StringVar()
        self.answer_1_confidence = IntVar()
        self.answer_2_confidence = IntVar()
        self.answer_3_confidence = IntVar()
        self.question.set('The Question text will go here.')
        self.answer_1.set('Answer 1')
        self.answer_2.set('Answer 2')
        self.answer_3.set('Answer 3')
        self.answer_1_confidence.set(100)
        self.answer_2_confidence.set(33)
        self.answer_3_confidence.set(33)
        self.master.title("HQ Trivia Bot")
        self.master.geometry("900x600+100+100")
        self.canvas = Canvas(self, offset=("0,-50"), background="#353C97")

    def update_question(self,question):
        self.question.set(question)
        self.canvas.pack_forget()
        self.initUI()

    def update_answers(self,answers):
        self.answer_1.set(answers['A'])
        self.answer_2.set(answers['B'])
        self.answer_3.set(answers['C'])
        self.canvas.pack_forget()
        self.initUI()

    def update_answer_confidences(self,confidence):
        self.answer_1_confidence.set(confidence['A'])
        self.answer_2_confidence.set(confidence['B'])
        self.answer_3_confidence.set(confidence['C'])
        self.canvas.pack_forget()
        self.initUI()

    def update_method_1(self,confidence):
        self.method_1.set(confidence)
        self.canvas.pack_forget()
        self.initUI()

    def update_method_2(self,confidence):
        self.method_2.set(confidence)
        self.canvas.pack_forget()
        self.initUI()

    def update_method_3(self,confidence):
        self.method_3.set(confidence)
        self.canvas.pack_forget()
        self.initUI()

    def initUI(self):

        self.pack(fill=BOTH, expand=1)

        # Drawing card background
        round_rectangle(10, 50, 330, 440, self.canvas,radius=20, fill="#FFF")

        # Draw the Question
        self.canvas.create_text(170, 180, font=("Superla Bold",22), fill="#222", width=250, justify=CENTER, text=self.question.get())

        # Drawing my button shapes
        self.canvas.create_oval(     25, 255, 70, 305, outline="#6DCAC3", fill="#6DCAC3", width=2)
        self.canvas.create_rectangle(50, 255, 290, 305, outline="#6DCAC3", fill="#6DCAC3", width=2, stipple="gray50")
        self.canvas.create_oval(     270, 255, 315, 305, outline="#6DCAC3", fill="#6DCAC3", width=2)
        self.canvas.create_text(     50,  280, font=("Superla Bold",20), anchor=W, text=self.answer_1.get())
        self.canvas.create_text(     295, 280, font=("Superla Bold",20), anchor=E, text=(str(self.answer_1_confidence.get())+'%'))

        # Drawing my button shapes
        self.canvas.create_oval(     25, 315, 70, 365, outline="#6DCAC3", fill="#6DCAC3", width=2)
        self.canvas.create_rectangle(50, 315, 290, 365, outline="#6DCAC3", fill="#6DCAC3", width=2)
        self.canvas.create_oval(    270, 315, 315, 365, outline="#6DCAC3", fill="#6DCAC3", width=2)
        self.canvas.create_text(    50,  340, font=("Superla Bold",20), anchor=W, text=self.answer_2.get())
        self.canvas.create_text(    295, 340, font=("Superla Bold",20), anchor=E, text=(str(self.answer_2_confidence.get())+'%'))

        # Drawing my button shapes
        self.canvas.create_oval(     25, 375, 70, 425, outline="#6DCAC3", fill="#6DCAC3", width=2)
        self.canvas.create_rectangle(50, 375, 290, 425, outline="#6DCAC3", fill="#6DCAC3", width=2)
        self.canvas.create_oval(     270, 375, 315, 425, outline="#6DCAC3", fill="#6DCAC3", width=2)
        self.canvas.create_text(     50, 400, font=("Superla Bold",20), anchor=W, text=self.answer_3.get())
        self.canvas.create_text(     295, 400, font=("Superla Bold",20), anchor=E, text=(str(self.answer_3_confidence.get())+'%'))

        # Draw the Text to the right of the card
        method_1_str = "Method 1: "+self.method_1.get()
        method_2_str = "Method 2: "+self.method_2.get()
        method_3_str = "Method 3: "+self.method_3.get()
        self.canvas.create_text(400, 150, font=("Superla",25), anchor=W, fill="#fff", width=450, text=method_1_str)
        self.canvas.create_text(400, 250, font=("Superla",25), anchor=W, fill="#fff", width=450, text=method_2_str)
        self.canvas.create_text(400, 350, font=("Superla",25), anchor=W, fill="#fff", width=450, text=method_3_str)

        self.canvas.pack(fill=BOTH, expand=1)
