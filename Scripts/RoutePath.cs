using Godot;
using System;
using System.Collections.Generic;

// One drivable service line: joined centreline points, the bus lane offset and source street per point.
public sealed class RoutePath
{
    public readonly List<Vector3> Points = new();
    public readonly List<float> Along = new(), Lanes = new();
    public readonly List<string> Streets = new();
    public readonly List<(float Distance, int Direction, string Street)> Turns = new();
    public float Length => Along.Count == 0 ? 0 : Along[^1];

    // Nathan Road keeps RoadMap's 5 m station spacing so H1 distances match the original service exactly.
    public void Add(Vector3 point, float lane, string street, float? along = null)
    {
        if (Points.Count > 0 && point.DistanceTo(Points[^1]) < .01f) return;
        Along.Add(along ?? (Points.Count == 0 ? 0 : Along[^1] + point.DistanceTo(Points[^1])));
        Points.Add(point); Lanes.Add(lane); Streets.Add(street);
    }

    private int Segment(float distance)
    {
        int index = Along.BinarySearch(Mathf.Clamp(distance, 0, Length));
        if (index < 0) index = ~index - 1;
        return Math.Clamp(index, 0, Points.Count - 2);
    }

    private static Vector3 Right(Vector3 a, Vector3 b) => new Vector3(b.X - a.X, 0, b.Z - a.Z).Normalized().Cross(Vector3.Up);

    private Vector3 Raw(float distance)
    {
        int i = Segment(distance);
        float t = Mathf.Clamp((distance - Along[i]) / Mathf.Max(Along[i + 1] - Along[i], .001f), 0, 1);
        return Points[i].Lerp(Points[i + 1], t);
    }

    // Government centrelines jog a few metres sideways through junctions. Harbour drives run on a
    // reference line averaged over ±8 m, with its normal from a 20 m chord, so a 15 m lane offset stays smooth.
    private readonly List<(Vector3 Centre, Vector3 Right)> _smooth = new();
    private const float SmoothStep = 2.5f;

    public void Smooth()
    {
        _smooth.Clear();
        for (float d = 0; d <= Length + SmoothStep; d += SmoothStep)
        {
            var centre = (Raw(d - 8) + Raw(d - 4) + Raw(d) + Raw(d + 4) + Raw(d + 8)) / 5;
            var chord = Raw(d + 10) - Raw(d - 10);
            _smooth.Add((centre, new Vector3(chord.X, 0, chord.Z).Normalized().Cross(Vector3.Up)));
        }
    }

    public Vector3 At(float distance, float lateral = 0)
    {
        if (_smooth.Count == 0)
        {
            int i = Segment(distance);
            return Raw(distance) + Right(Points[i], Points[i + 1]) * lateral;
        }
        float at = Mathf.Clamp(distance, 0, Length) / SmoothStep;
        int k = Math.Min((int)at, _smooth.Count - 2);
        float u = at - k;
        var (c0, r0) = _smooth[k]; var (c1, r1) = _smooth[k + 1];
        return c0.Lerp(c1, u) + r0.Lerp(r1, u).Normalized() * lateral;
    }

    public float BaseLane(float distance)
    {
        int i = Segment(distance);
        float t = Mathf.Clamp((distance - Along[i]) / Mathf.Max(Along[i + 1] - Along[i], .001f), 0, 1);
        return Mathf.Lerp(Lanes[i], Lanes[i + 1], t);
    }

    public string StreetAt(float distance) => Streets[Segment(distance)];
    public Vector3 Forward(float distance) => (At(distance + 2) - At(distance - 2)).Normalized();
    public float Heading(float distance) => Mathf.Atan2(-Forward(distance).X, -Forward(distance).Z);

    // Height joins plan distance so a deep tunnel never projects onto the street above it.
    public (float Distance, float Lateral, float Gap) Project(Vector3 position)
    {
        float best = float.MaxValue, along = 0, lateral = 0;
        int count = _smooth.Count > 0 ? _smooth.Count : Points.Count;
        for (int i = 0; i < count - 1; i++)
        {
            var a = _smooth.Count > 0 ? _smooth[i].Centre : Points[i];
            var b = _smooth.Count > 0 ? _smooth[i + 1].Centre : Points[i + 1];
            var delta = b - a;
            var flat = new Vector3(delta.X, 0, delta.Z);
            var offset = new Vector3(position.X - a.X, 0, position.Z - a.Z);
            float t = Mathf.Clamp(offset.Dot(flat) / Mathf.Max(flat.LengthSquared(), .0001f), 0, 1);
            var side = offset - flat * t;
            float height = position.Y - Mathf.Lerp(a.Y, b.Y, t);
            float score = side.LengthSquared() + height * height;
            if (score >= best) continue;
            best = score;
            along = _smooth.Count > 0 ? (i + t) * SmoothStep : Along[i] + (Along[i + 1] - Along[i]) * t;
            lateral = side.Dot(_smooth.Count > 0 ? _smooth[i].Right.Lerp(_smooth[i + 1].Right, t).Normalized() : Right(a, b));
        }
        return (Mathf.Min(along, Length), lateral, Mathf.Sqrt(best));
    }

    // Junction turns: chord headings 10-35 m either side differ by over 40 degrees; centreline jogs cancel out.
    private float Chord(float from, float to) { var d = At(to) - At(from); return Mathf.Atan2(-d.X, -d.Z); }

    public void FindTurns()
    {
        Turns.Clear();
        float start = -1, peak = 0, sharpest = 0;
        for (float d = 35; d <= Length - 35; d += 2.5f)
        {
            float change = Mathf.AngleDifference(Chord(d - 35, d - 10), Chord(d + 10, d + 35));
            if (Mathf.Abs(change) > Mathf.DegToRad(40))
            {
                if (start < 0) { start = d; sharpest = 0; }
                if (Mathf.Abs(change) > Mathf.Abs(sharpest)) { sharpest = change; peak = d; }
            }
            else if (start >= 0)
            {
                Turns.Add((peak, Math.Sign(sharpest), StreetAt(Mathf.Min(Length, peak + 25))));
                start = -1;
            }
        }
    }

    public (float Distance, int Direction, string Street)? NextTurn(float distance, float range)
    {
        foreach (var turn in Turns)
            if (turn.Distance > distance - 4 && turn.Distance < distance + range) return turn;
        return null;
    }
}
