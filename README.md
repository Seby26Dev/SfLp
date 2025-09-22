<img width="1420" height="376" alt="image" src="https://github.com/user-attachments/assets/2b25dfd6-cb74-4473-a672-a35526e82b34" />
# SfLp
Script for lazy people


# This script automatizate the WriteOwner -> Group -> GenericWrite


### How to use the script 

You will use WoGr.py // and WoGr_rights.py 

<img width="698" height="245" alt="image" src="https://github.com/user-attachments/assets/fc760e9e-87a8-458b-9951-ca4a0901486b" />


<img width="741" height="186" alt="image" src="https://github.com/user-attachments/assets/72030468-6d11-4b7f-b45c-1036c05f60de" />



1) Chmod
```
chmod +x WoGr.py WoGr_rights.py
```
2) Run WoGr.py

```
python3 WoGr.py -u USER -p PASSWORD -d DOMAIN -t TARGET --dc DC [--exp EXP]
```
2 exp)
```
python3 WoGr.py -u judith.mader -p judith09 -d certified.htb -t management_svc --dc 10.10.11.41 --exp "management_svc.ccache"
```
2 ) If script get the errot "INSUFF_ACCESS_RIGHTS" run WoGr_rights.py

<img width="1420" height="376" alt="image" src="https://github.com/user-attachments/assets/dc4fd7dd-58a9-47eb-81c6-cf5bc6c7e182" />




# EXP

<img width="1201" height="370" alt="image" src="https://github.com/user-attachments/assets/cef31768-6ec0-4bdc-9011-1ddb34d13de4" />

 - 1 User we own -u , -p in WoGr.py 

