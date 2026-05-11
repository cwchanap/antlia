env = SConscript("godot-cpp/SConstruct")

env.Append(CPPPATH=["src"])
env.Append(CXXFLAGS=["-std=c++17"])

sources = Glob("src/*.cpp") + Glob("src/driving/*.cpp")

library_path = f'bin/libantlia{env["suffix"]}{env["SHLIBSUFFIX"]}'

library = env.SharedLibrary(library_path, source=sources)
Default(library)
