import cv2
import mediapipe as mp
import numpy as np
import time
import sys
import keyboard
from time import sleep

def press_key(key_code):
    """Press and release a key using keyboard library"""
    try:
        keyboard.press(key_code)  # Press key
        sleep(0.1)  # Very short hold for fast response
        keyboard.release(key_code)
        sleep(0.05)  # Minimal delay
    except Exception as e:
        print(f"Error pressing key: {e}")

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,  # Lower threshold for faster detection
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

# Initialize the webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Check if camera opened successfully
if not cap.isOpened():
    print("Error: Could not open camera")
    sys.exit(1)

# Get actual camera resolution
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Camera Resolution: {frame_width}x{frame_height}")

# Game state
game_started = True
last_gesture = None
gesture_cooldown = 0.05  # Very short cooldown for immediate response
last_gesture_time = time.time()

# Movement smoothing
gesture_history = []
HISTORY_SIZE = 1  # Minimal history for immediate response
REQUIRED_CONSECUTIVE = 1  # Trigger on first detection

def get_hand_center(hand_landmarks):
    """Calculate the center point of the hand"""
    x_coords = [landmark.x for landmark in hand_landmarks.landmark]
    y_coords = [landmark.y for landmark in hand_landmarks.landmark]
    center_x = sum(x_coords) / len(x_coords)
    center_y = sum(y_coords) / len(y_coords)
    return center_x, center_y

def detect_gesture(hand_landmarks, prev_center=None):
    """Detect the type of gesture based on hand landmarks"""
    center_x, center_y = get_hand_center(hand_landmarks)
    
    if prev_center is None:
        return "NONE", (center_x, center_y)
    
    prev_x, prev_y = prev_center
    
    # Calculate movement
    dx = center_x - prev_x
    dy = center_y - prev_y
    
    # Very sensitive thresholds for immediate response
    vertical_threshold = 0.02
    horizontal_threshold = 0.02
    
    # Check both vertical and horizontal movement
    if abs(dy) > vertical_threshold:
        if dy < 0:
            return "UP", (center_x, center_y)
        else:
            return "DOWN", (center_x, center_y)
    
    if abs(dx) > horizontal_threshold:
        if dx > 0:
            return "RIGHT", (center_x, center_y)
        else:
            return "LEFT", (center_x, center_y)
            
    return "NONE", (center_x, center_y)

def detect_hands_together(results):
    """Detect if both hands are close to each other"""
    if not results.multi_hand_landmarks or len(results.multi_hand_landmarks) < 2:
        return False
    
    hand1_center = get_hand_center(results.multi_hand_landmarks[0])
    hand2_center = get_hand_center(results.multi_hand_landmarks[1])
    
    distance = np.sqrt((hand1_center[0] - hand2_center[0])**2 + 
                      (hand1_center[1] - hand2_center[1])**2)
    
    return distance < 0.3

def should_trigger_gesture(gesture):
    """Check if a gesture should be triggered based on history"""
    global gesture_history
    
    gesture_history.append(gesture)
    if len(gesture_history) > HISTORY_SIZE:
        gesture_history.pop(0)
    
    # Count consecutive occurrences of the current gesture
    consecutive_count = 0
    for g in reversed(gesture_history):
        if g == gesture:
            consecutive_count += 1
        else:
            break
            
    return consecutive_count >= REQUIRED_CONSECUTIVE

def simulate_keypress(gesture):
    """Simulate a key press based on gesture"""
    try:
        if gesture == "UP":
            press_key('up')
        elif gesture == "DOWN":
            press_key('down')
        elif gesture == "LEFT":
            press_key('left')
        elif gesture == "RIGHT":
            press_key('right')
        elif gesture == "SPACE":
            press_key('space')
    except Exception as e:
        print(f"Error simulating keypress: {e}")

def draw_direction_arrow(frame, gesture):
    """Draw an arrow indicating the detected movement direction"""
    height, width = frame.shape[:2]
    center_x, center_y = width // 2, height // 2
    arrow_length = 50
    arrow_color = (0, 255, 0)  # Green
    thickness = 3

    if gesture == "UP":
        start_point = (center_x, center_y + arrow_length)
        end_point = (center_x, center_y - arrow_length)
    elif gesture == "DOWN":
        start_point = (center_x, center_y - arrow_length)
        end_point = (center_x, center_y + arrow_length)
    elif gesture == "LEFT":
        start_point = (center_x + arrow_length, center_y)
        end_point = (center_x - arrow_length, center_y)
    elif gesture == "RIGHT":
        start_point = (center_x - arrow_length, center_y)
        end_point = (center_x + arrow_length, center_y)
    else:
        return

    cv2.arrowedLine(frame, start_point, end_point, arrow_color, thickness, tipLength=0.3)

prev_hand_center = None
frame_count = 0
fps_start_time = time.time()

print("\nStarting hand gesture control...")
print("IMPORTANT SETUP STEPS:")
print("1. Open Chrome and go to Subway Surfers")
print("2. Position the game window on the right side")
print("3. Click on the game window once to focus it")
print("\nGesture Controls:")
print("↑ Raise hand UP to JUMP")
print("↓ Lower hand DOWN to ROLL")
print("← Move hand LEFT to go LEFT")
print("→ Move hand RIGHT to go RIGHT")
print("Press 'q' to quit\n")

# Give user time to switch to game window
print("Starting in:")
for i in range(3, 0, -1):
    print(f"{i}...")
    sleep(1)
print("Go!")

try:
    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to capture frame")
            break

        # Calculate FPS
        frame_count += 1
        if frame_count % 30 == 0:
            fps = frame_count / (time.time() - fps_start_time)
            print(f"FPS: {fps:.2f}")

        # Flip the frame horizontally for a later selfie-view display
        frame = cv2.flip(frame, 1)
        
        # Convert the BGR image to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame and detect hands
        results = hands.process(rgb_frame)
        
        # Draw hand landmarks and detect gestures
        current_gesture = "NONE"
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Get gesture for the first hand
            gesture, current_center = detect_gesture(results.multi_hand_landmarks[0], prev_hand_center)
            prev_hand_center = current_center
            current_gesture = gesture
            
            # Check if enough time has passed since last gesture
            current_time = time.time()
            if current_time - last_gesture_time >= gesture_cooldown:
                if gesture != "NONE":
                    if should_trigger_gesture(gesture):
                        print(f"{gesture}!")
                        simulate_keypress(gesture)
                        last_gesture_time = current_time
        
        # Draw direction arrow for the current gesture
        if current_gesture != "NONE":
            draw_direction_arrow(frame, current_gesture)
        
        # Display current gesture only
        cv2.putText(frame, f"Current: {current_gesture}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Display the frame with a simple title
        cv2.imshow('Hand Control', frame)
        
        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    print("Cleaning up...")
    cap.release()
    cv2.destroyAllWindows()
