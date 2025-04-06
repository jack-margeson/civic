// Testing program for the CIVIC server framework.
// Takes an input file with one letter of the alphabet (a)
// and creates an output file with the next letter of the alphabet. (a->b).
// The program will also burn CPU cycles to simulate a real program, between 1 and 5 seconds.

// INPUT: [{"letter":"a"}]
// If the input file is 'z', the output file will be 'a'.
// If the input file is empty, the output file will be empty.
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

    srand(time(NULL));
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

    char ch;
    char buffer[256];

    // Read the input file as JSON
    if (fgets(buffer, sizeof(buffer), in) == NULL) {
        // If the input file is empty or invalid, leave the output file empty
        fprintf(stderr, "Error: Input file is empty or invalid.\n");
        fclose(in);
        fclose(out);
        return;
    }

    // Parse the JSON to extract the "letter" field
    char *start = strstr(buffer, "\"letter\":");
    if (!start) {
        // If the "letter" field is not found, leave the output file empty
        fprintf(stderr, "Error: \"letter\" field not found in input file.\n");
        fclose(in);
        fclose(out);
        return;
    }

    start += strlen("\"letter\":");
    while (*start && (*start == ' ' || *start == '\"')) start++;

    ch = *start;
    if (*start == '\0' || *(start + 1) != '\"') {
        fprintf(stderr, "Error: Invalid JSON format for \"letter\" field.\n");
        fclose(in);
        fclose(out);
        return;
    }

    // Check if the character is a lowercase letter
    if (!islower(ch)) {
        fprintf(stderr, "Error: Character is not a lowercase letter.\n");
        fclose(in);
        fclose(out);
        return;
    }

    char next_char = (ch == 'z') ? 'a' : ch + 1;
    
    // Write the next character to the output file in JSON format
    fprintf(out, "[{\"original_letter\": \"%c\", \"letter\": \"%c\"}]\n", ch, next_char);

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