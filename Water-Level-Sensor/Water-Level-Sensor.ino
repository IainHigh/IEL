// include the library code:
#include <LiquidCrystal.h>

// initialize the library by associating any needed LCD interface pin
// with the arduino pin number it is connected to
const int rs = 2, en = 3, d4 = 9, d5 = 10, d6 = 11, d7 = 12;
LiquidCrystal lcd(rs, en, d4, d5, d6, d7);

// defines pins numbers
const int powerPin = 7;
const int trigPin = 6;
const int echoPin = 5;
double averageDepth;
int counter = 0;

// defines variables
long duration;
int distance;
void setup() {
  lcd.begin(16, 2);

  // Use pin 7 as a 5v output for the sensor.
  pinMode(powerPin, OUTPUT);
  digitalWrite(powerPin, HIGH);
  
  pinMode(trigPin, OUTPUT); // Sets the trigPin as an Output
  pinMode(echoPin, INPUT); // Sets the echoPin as an Input
  Serial.begin(9600); // Starts the serial communication

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Calibrating...");
}
void loop() {
  // Clears the trigPin
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  // Sets the trigPin on HIGH state for 10 micro seconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  // Reads the echoPin, returns the sound wave travel time in microseconds
  duration = pulseIn(echoPin, HIGH);
  // Calculating the distance
  double distance = duration * 0.029 / 2;

  if (millis() < 5000){
    // Calibration stage, calculate the distance to the bottom of the cup.
    if (distance < 500 and distance > 0){
      averageDepth += distance;
      counter += 1;
    }
    lcd.setCursor(0, 1);
    lcd.print(millis() / 1000);
    lcd.print(" / 5");
    delay(50);
    
  }
  else{
    int c2 = 0;
    double test = 0;
    for (int i = 0; i < 10; i++){
      test += (averageDepth/counter) - distance;
      c2 += 1;
      delay(50);
    }
    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("Water Level:");
    lcd.setCursor(0, 1);
    lcd.print(test/c2);
    lcd.print("cm");
  }
  
  
  
  
}
