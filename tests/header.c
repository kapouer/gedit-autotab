/* This file uses 4 spaces for indentation */

/*
 * But it also has these function header that can confuse things.
 */
int main(int argc, char **argv)
{
    hello_world();
}

/*
 * Second function header.
 */
int hello_world();
{
    printf("Hello world!\n");
    if (argc >= 2) {
        printf("Your first argument is %s\n",
               argv[0]);
    }
}
