import tkinter as tk
from tkinter import messagebox
import mysql.connector
import pygame
import os
import time
import random

# Connect to MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="your_password",
    database="game"
)
cursor = db.cursor()

def signup(username_entry, password_entry, security_question_var, security_answer_entry):
    username = username_entry.get()
    password = password_entry.get()
    security_question = security_question_var.get()
    security_answer = security_answer_entry.get()


    if len(username) > 15 or len(password) > 15:
        messagebox.showerror("Error", "Username and password cannot exceed 15 characters")
        return

    if username == "" or password == ""  or security_question == "" or security_answer == "":
        messagebox.showerror("Error", "Please fill in all fields")
        return

    # Check if username already exists
    cursor.execute("select * from users where username = %s", (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        messagebox.showerror("Error", "Username already exists. Please enter a different username.")
        return

    # Insert new user into database
    cursor.execute("insert into users (username, password, security_question, security_answer) values (%s, %s, %s, %s)", (username, password, security_question, security_answer))
    db.commit()
    messagebox.showinfo("Success", "User registered successfully")

def login(username_entry, password_entry):
    username = username_entry.get()
    password = password_entry.get()

    if username == "" or password == "":
        messagebox.showerror("Error", "Please enter both username and password")
        return

    # Check if username and password match
    cursor.execute("select * from users where binary username = %s and binary password = %s", (username, password))
    user = cursor.fetchone()

    if user:
        messagebox.showinfo("Success", "Login successful")
        root.destroy()
        # Launch game here
        launch_game(username)
    else:
        messagebox.showerror("Error", "Invalid username or password")

def forgot_password(username_entry, security_answer_entry):
    username = username_entry.get()
    security_answer = security_answer_entry.get().lower()

    if username == "" or security_answer == "":
        messagebox.showerror("Error", "Please enter your username and answer the security question")
        return

    # Retrieve security question and answer for the given username
    cursor.execute("select security_question, security_answer from users where binary username = %s", (username,))
    user_data = cursor.fetchone()

    if not user_data:
        messagebox.showerror("Error", "Username not found")
        return

    correct_security_question, correct_security_answer = user_data

    if security_answer == correct_security_answer.lower():
        cursor.execute("select password from users where username = %s", (username,))
        password = cursor.fetchone()[0]
        messagebox.showinfo("Password Recovery", f"Your password is: {password}")
    else:
        messagebox.showerror("Error", "Incorrect answer to security question")

def delete_account(username_entry, password_entry):
    username = username_entry.get()
    password = password_entry.get()

    if username == "" or password == "":
        messagebox.showerror("Error", "Please enter both username and password")
        return

    # Check if username and password match
    cursor.execute("select * from users where binary username = %s and binary password = %s", (username, password))
    user = cursor.fetchone()

    if user:
        confirmation = messagebox.askyesno("Confirmation", "Are you sure you want to delete your account?")
        if confirmation:
            # Delete the user from the database
            cursor.execute("delete from users where username = %s", (username,))
            db.commit()
            messagebox.showinfo("Success", "Account deleted successfully")
        else:
            messagebox.showinfo("Info", "Account deletion canceled")
    else:
        messagebox.showerror("Error", "Invalid username or password")


# Function to update high score in the database
def update_high_score(username, score):
    cursor.execute("select high_score from users where username = %s", (username,))
    current_high_score = cursor.fetchone()[0]
    if score > current_high_score:
        cursor.execute("update users set high_score = %s where username = %s", (score, username))
        db.commit()

def launch_game(username):
    pygame.font.init()

    # Window
    WIDTH, HEIGHT = 750, 750
    WINDOW = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Space Adventure Game")

    # Loading Enemy Ships
    RED_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_red_small.png"))
    GREEN_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_green_small.png"))
    BLUE_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_blue_small.png"))

    # Loading Player Ship
    YELLOW_SPACE_SHIP = pygame.image.load(os.path.join("assets", "pixel_ship_yellow.png"))

    # Loading Lasers
    RED_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_red.png"))
    GREEN_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_green.png"))
    BLUE_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_blue.png"))
    YELLOW_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_yellow.png"))

    # Loading Background Image
    BG = pygame.transform.scale(pygame.image.load(os.path.join("assets", "background-black.png")), (WIDTH, HEIGHT))

    score = 0

    class Laser:
        def __init__(self, x, y, img):
            self.x = x
            self.y = y
            self.img = img
            self.mask = pygame.mask.from_surface(self.img)

        def draw(self, window):
            window.blit(self.img, (self.x, self.y))

        def move(self, vel):
            self.y += vel

        def off_screen(self, height):
            return not(self.y <= height and self.y >= 0)

        def collision(self, obj):
            return collide(self, obj)

    class Ship:
        COOLDOWN = 30

        def __init__(self, x, y, health=100):
            self.x = x
            self.y = y
            self.health = health
            self.ship_img = None
            self.laser_img = None
            self.lasers = []
            self.cool_down_counter = 0

        def draw(self, window):
            window.blit(self.ship_img, (self.x, self.y))
            for laser in self.lasers:
                laser.draw(window)

        def move_lasers(self, vel, obj):
            self.cooldown()
            for laser in self.lasers:
                laser.move(vel)
                if laser.off_screen(HEIGHT):
                    self.lasers.remove(laser)
                elif laser.collision(obj):
                    obj.health -= 10
                    self.lasers.remove(laser)

        def cooldown(self):
            if self.cool_down_counter >= self.COOLDOWN:
                self.cool_down_counter = 0
            elif self.cool_down_counter > 0:
                self.cool_down_counter += 1

        def shoot(self):
            if self.cool_down_counter == 0:
                laser = Laser(self.x, self.y, self.laser_img)
                self.lasers.append(laser)
                self.cool_down_counter = 1

        def get_width(self):
            return self.ship_img.get_width()

        def get_height(self):
            return self.ship_img.get_height()

    class Player(Ship):

        def __init__(self, x, y, health=100):
            super().__init__(x, y, health)
            self.ship_img = YELLOW_SPACE_SHIP
            self.laser_img = YELLOW_LASER
            self.mask = pygame.mask.from_surface(self.ship_img)
            self.max_health = health

        def move_lasers(self, vel, objs):
            global score
            self.cooldown()
            for laser in self.lasers:
                laser.move(vel)
                if laser.off_screen(HEIGHT):
                    self.lasers.remove(laser)
                else:
                    for obj in objs:
                        if laser.collision(obj):
                            objs.remove(obj)
                            score += 1
                            if laser in self.lasers:
                                self.lasers.remove(laser)

        def draw(self, window):
            super().draw(window)
            self.healthbar(window)

        def healthbar(self, window):
            pygame.draw.rect(window, (255,0,0), (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width(), 10))
            pygame.draw.rect(window, (0,255,0), (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width() * (self.health/self.max_health), 10))

        pygame.display.update()

    class Enemy(Ship):
        COLOR_MAP = {
                    "red": (RED_SPACE_SHIP, RED_LASER),
                    "green": (GREEN_SPACE_SHIP, GREEN_LASER),
                    "blue": (BLUE_SPACE_SHIP, BLUE_LASER)
                    }
        def __init__(self, x, y, color, health=100):
            super().__init__(x, y, health)
            self.ship_img, self.laser_img = self.COLOR_MAP[color]
            self.mask = pygame.mask.from_surface(self.ship_img)

        def move(self, vel):
            self.y += vel

        def shoot(self):
            if self.cool_down_counter == 0:
                laser = Laser(self.x-20, self.y, self.laser_img)
                self.lasers.append(laser)
                self.cool_down_counter = 1

    def collide(obj1, obj2):
        offset_x = obj2.x - obj1.x
        offset_y = obj2.y - obj1.y
        return obj1.mask.overlap(obj2.mask, (offset_x, offset_y)) != None
    
    def game_over(score):
        # Calculate the final score
        final_score = score
        # Update high score in the database
        update_high_score(username, final_score)

    def main():
        run = True
        FPS = 60
        level = 0
        lives = 5
        global score
        score = 0
        cursor.execute("select high_score from users where username = %s", (username,))
        user_high_score = cursor.fetchone()[0]

        main_font = pygame.font.SysFont("comicsans", 50)
        lost_font = pygame.font.SysFont("comicsans", 60)

        enemies = []
        wave_length = 5

        enemy_vel = 1
        player_vel = 5
        laser_vel = 5 

        player = Player(325, 630)

        clock = pygame.time.Clock()

        lost = False
        lost_count = 0

        def redraw_window():
            WINDOW.blit(BG, (0,0))

            for enemy in enemies:
                enemy.draw(WINDOW)

            player.draw(WINDOW)

            # Adding text of lives, level and score
            lives_label = main_font.render(f"Lives: {lives}", 1, (255,255,255))
            level_label = main_font.render(f"Level: {level}", 1, (255,255,255))
            score_label = main_font.render("Score: "+ str(score), 1, (255,255,255))
            high_score_label = main_font.render("High Score: " + str(user_high_score), 1, (255,255,255))

            WINDOW.blit(lives_label, (10, 10))
            WINDOW.blit(level_label, (WIDTH - level_label.get_width() - 10, 10))
            WINDOW.blit(score_label, (WIDTH/2 - score_label.get_width()/2, 10))
            WINDOW.blit(high_score_label, (WIDTH/2 - high_score_label.get_width()/2, 50))

            if lost:
                lost_label = lost_font.render("You Lost!!", 1, (255,255,255))

                WINDOW.blit(lost_label, (WIDTH/2 - lost_label.get_width()/2, 350))  

            pygame.display.update()

        while run:
            clock.tick(FPS)
            redraw_window()

            if lives <= 0 or player.health <= 0:
                game_over(score)
                lost = True
                lost_count += 1

            if lost:
                if lost_count > FPS * 5:
                    run = False
                else:
                    continue

            if len(enemies) == 0:
                level += 1
                wave_length += 5
                for i in range(wave_length):
                    enemy = Enemy(random.randrange(50, WIDTH-100), random.randrange(-1500, -100), random.choice(["red", "blue", "green"]))
                    enemies.append(enemy)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()

            keys = pygame.key.get_pressed()
            if keys[pygame.K_a] and player.x - player_vel > 0:  # Move Left
                player.x -= player_vel
            if keys[pygame.K_d] and player.x + player_vel + player.get_width() < WIDTH:  # Move Right
                player.x += player_vel
            if keys[pygame.K_w] and player.y - player_vel > 0:  # Move Up
                player.y -= player_vel
            if keys[pygame.K_s] and player.y + player_vel + player.get_height() + 15 < HEIGHT:  # Move Down
                player.y += player_vel
            if keys[pygame.K_SPACE]:
                player.shoot()

            for enemy in enemies[:]:
                enemy.move(enemy_vel)
                enemy.move_lasers(laser_vel, player)

                if random.randrange(0, 3*60) == 1:
                    enemy.shoot()

                if collide(enemy, player):
                    player.health -= 10
                    enemies.remove(enemy)
                elif enemy.y + enemy.get_height() > HEIGHT:
                    lives -= 1
                    enemies.remove(enemy)
            
            player.move_lasers(-laser_vel, enemies)

    def main_menu():
        title_font = pygame.font.SysFont("comicsans", 50)
        title2_font = pygame.font.SysFont("comicsans", 38)
        run = True
        while run:
            WINDOW.blit(BG, (0,0))
            title2_label = title2_font.render("Welcome To The Space Adventure Game", 1, (255,255,255))
            title_label = title_font.render("Press Enter key to begin...", 1, (255,255,255))
            WINDOW.blit(title2_label, (WIDTH/2 - title2_label.get_width()/2, 340 - title_label.get_height()))
            WINDOW.blit(title_label, (WIDTH/2 - title_label.get_width()/2, 350))
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                keys2 = pygame.key.get_pressed()
                if keys2[pygame.K_RETURN]:
                    main()
        pygame.quit()

    main_menu()

# Create UI
root = tk.Tk()
root.title("Space Adventure Game")

# Set window size
window_width = 600
window_height = 300
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width / 2) - (window_width / 2)
y = (screen_height / 2) - (window_height / 2)
root.geometry(f"{window_width}x{window_height}+{int(x)}+{int(y)}")


# Username label and entry
username_label = tk.Label(root, text="Username:")
username_label.grid(row=1, column=0, padx=10, pady=5)
username_entry = tk.Entry(root)
username_entry.grid(row=1, column=1, padx=10, pady=5)

# Password label and entry
password_label = tk.Label(root, text="Password:")
password_label.grid(row=1, column=2, padx=10, pady=5)
password_entry = tk.Entry(root, show="*")
password_entry.grid(row=1, column=3, padx=10, pady=5)

# Security question label and dropdown menu
security_question_label = tk.Label(root, text="Security Question:")
security_question_label.grid(row=2, column=0, padx=10, pady=5)

security_questions = ["What is your favorite car?", "What is your mother's name?", "In which city were you born?"]
security_question_var = tk.StringVar(root)
security_question_var.set(security_questions[0])  # Default value

security_question_menu = tk.OptionMenu(root, security_question_var, *security_questions)
security_question_menu.grid(row=2, column=1, padx=10, pady=5)

# Security answer label and entry
security_answer_label = tk.Label(root, text="Security Answer:")
security_answer_label.grid(row=2, column=2, padx=10, pady=5)
security_answer_entry = tk.Entry(root)
security_answer_entry.grid(row=2, column=3, padx=10, pady=5)

# Signup button
signup_button = tk.Button(root, text="Signup", command=lambda: signup(username_entry, password_entry, security_question_var, security_answer_entry))
signup_button.grid(row=5, column=1, padx=10, pady=5)

# Login button
login_button = tk.Button(root, text="Login", command=lambda: login(username_entry, password_entry))
login_button.grid(row=5, column=2, padx=10, pady=5)

# Forgot password button
forgot_password_button = tk.Button(root, text="Forgot Password", command=lambda: forgot_password(username_entry, security_answer_entry))
forgot_password_button.grid(row=6, column=1, columnspan=2, padx=10, pady=5)

#  Delete account button
delete_account_button = tk.Button(root, text="Delete Account", command=lambda: delete_account(username_entry, password_entry))
delete_account_button.grid(row=7, column=1, columnspan=2, padx=10, pady=5)

root.mainloop()