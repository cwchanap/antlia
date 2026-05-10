#pragma once

#include <cmath>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace antlia::test {

using TestFn = std::function<void()>;

struct TestCase {
    std::string name;
    TestFn run;
};

inline std::vector<TestCase> &registry() {
    static std::vector<TestCase> tests;
    return tests;
}

struct Registrar {
    Registrar(const std::string &name, TestFn run) {
        registry().push_back({name, run});
    }
};

inline void check(bool condition, const char *expression, const char *file, int line) {
    if (!condition) {
        throw std::runtime_error(std::string(file) + ":" + std::to_string(line) + " CHECK failed: " + expression);
    }
}

inline void check_near(double actual, double expected, double tolerance, const char *expression, const char *file, int line) {
    if (std::fabs(actual - expected) > tolerance) {
        throw std::runtime_error(
            std::string(file) + ":" + std::to_string(line) + " CHECK_NEAR failed: " + expression +
            " actual=" + std::to_string(actual) +
            " expected=" + std::to_string(expected) +
            " tolerance=" + std::to_string(tolerance));
    }
}

inline int run_all() {
    int failures = 0;
    for (const TestCase &test : registry()) {
        try {
            test.run();
            std::cout << "[PASS] " << test.name << "\n";
        } catch (const std::exception &error) {
            ++failures;
            std::cerr << "[FAIL] " << test.name << "\n" << error.what() << "\n";
        }
    }

    std::cout << registry().size() - failures << " passed, " << failures << " failed\n";
    return failures == 0 ? 0 : 1;
}

} // namespace antlia::test

#define ANTLIA_TEST(name) \
    static void name(); \
    static ::antlia::test::Registrar name##_registrar(#name, name); \
    static void name()

#define CHECK(expression) ::antlia::test::check((expression), #expression, __FILE__, __LINE__)
#define CHECK_NEAR(actual, expected, tolerance) \
    ::antlia::test::check_near((actual), (expected), (tolerance), #actual " ~= " #expected, __FILE__, __LINE__)
