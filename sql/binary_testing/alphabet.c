// Testing program for the CIVIC server framework.
// Takes an input file with one letter of the alphabet (a)
// and creates an output file with the next letter of the alphabet. (a->b).
// The program will also burn CPU cycles to simulate a real program, between 1 and 5 seconds.


// If the input file is not a letter of the alphabet, the output file will be empty.
// If the input file is 'z', the output file will be 'a'.
// If the input file is empty, the output file will be empty.
// If the input file is not a single character, the output file will be empty.
// If the input file is a letter of the alphabet, but not lowercase, the output file will be empty.


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>

void process_file(const char *input_file, const char *output_file);
void burn_cpu(float seconds);

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <input_file> <output_file>\n", argv[0]);
        return 1;
    }

    process_file(argv[1], argv[2]);
    return 0;
}

void process_file(const char *input_file, const char *output_file) {
    FILE *in = fopen(input_file, "r");
    if (!in) {
        perror("Error opening input file");
        return;
    }

    FILE *out = fopen(output_file, "w");
    if (!out) {
        perror("Error opening output file");
        fclose(in);
        return;
    }

    int ch = fgetc(in);
    if (ch == EOF || !islower(ch) || fgetc(in) != EOF) {
        // Input file is empty, not a single lowercase letter, or has more than one character
        fclose(in);
        fclose(out);
        return;
    }

    char next_char = (ch == 'z') ? 'a' : ch + 1;
    fprintf(out, " %c->%c ", ch, next_char);

    fclose(in);
    fclose(out);

    // Burn CPU cycles
    float burn_time = 1.0f + ((float)rand() / RAND_MAX) * 4.0f;
    burn_cpu(burn_time);
}

void burn_cpu(float seconds) {
    clock_t start_time = clock();
    while ((clock() - start_time) < seconds * CLOCKS_PER_SEC) {
        // Burn CPU cycles
        // We have to actually do something in this loop, otherwise the compiler will optimize it away
        volatile int result = 0;
        for (int i = 0; i < 1000; i++) {
            for (int j = 0; j < 1000; j++) {
                result += i * j;
            }
        }
    }
    // Print how long the CPU was burned for
    printf("Burned CPU for %f seconds\n", seconds);
}