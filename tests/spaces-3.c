/* This file uses 3 spaces for indentation */

int main(int argc, char **argv)
{
   printf("Hello world!\n");
   if (argc >= 2) {
      printf("Your first argument is %s\n",
             argv[0]);
   }
}
