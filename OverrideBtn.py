from Tkinter import *
import sharedVars

class ovrBtn:
    def __init__(self):
        window = Tk()
        self.window = window
        self.window.title('Override-Mircrophone!')

        #initialize button
        self.overrideBtn = Button(window,
                                  text = "Start Override",
                                  command=self.switch,
                                  font=("Helvetica",24),
                                  activebackground="green")
        
        #opens window and displays override button

        self.overrideBtn.pack(padx=20, pady=30)

    def openButton(self):
        self.window.mainloop()

    def switch(self):
        if sharedVars.ISRECORDING:
            sharedVars.ISRECORDING = False
            self.overrideBtn.config(text="Start Override.", fg="green")
            print("Override stopped...")

        else:
            sharedVars.ISRECORDING = True
            self.overrideBtn.config(text="Stop Overriding.", fg="red")
            print("Override began")

if __name__ == "__main__":
    button = ovrBtn()
    button.openButton()
